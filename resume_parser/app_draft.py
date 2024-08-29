from flask import Flask, request, redirect, url_for, render_template, flash
from werkzeug.utils import secure_filename
import os
import docx
import MySQLdb
from config import Config
from datetime import datetime
import re
import spacy
from spacy.pipeline import EntityRuler
from spacy.language import Language
from pdfminer.converter import TextConverter
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.layout import LAParams
from pdfminer.pdfpage import PDFPage
import io

# Load spaCy model
nlp = spacy.load('en_core_web_sm')

# Create an EntityRuler
@Language.factory("education_entity_ruler")
def create_education_ruler(nlp, name):
    ruler = EntityRuler(nlp)
    patterns = [
        {"label": "EDUCATION", "pattern": "Bachelor"},
        {"label": "EDUCATION", "pattern": "Master"},
        {"label": "EDUCATION", "pattern": "PhD"},
        {"label": "EDUCATION", "pattern": "Diploma"},
        {"label": "EDUCATION", "pattern": "Certificate"},
        {"label": "EDUCATION", "pattern": "College"},
        {"label": "EDUCATION", "pattern": "High School"},
        {"label": "EDUCATION", "pattern": "Senior High"},
        {"label": "EDUCATION", "pattern": "Junior High"},
        {"label": "EDUCATION", "pattern": "Elementary"},
    ]
    ruler.add_patterns(patterns)
    return ruler

# Add the EntityRuler to the pipeline
if 'education_entity_ruler' not in nlp.pipe_names:
    nlp.add_pipe('education_entity_ruler', last=True)
else:
    print("EntityRuler already in the pipeline.")

# Save the spaCy model to disk
nlp.to_disk("trained_spacy_model")

app = Flask(__name__)
app.config.from_object(Config)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

db = MySQLdb.connect(
    host=app.config['MYSQL_HOST'],
    user=app.config['MYSQL_USER'],
    passwd=app.config['MYSQL_PASSWORD'],
    db=app.config['MYSQL_DB']
)

# Define the path to the skills.txt file
skills_file_path = os.path.join(os.path.dirname(__file__), 'skills.txt')

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def clean_text(text):
    text = text.replace('\n', ' ')  # Replace newlines with spaces
    text = re.sub(r'\s+', ' ', text)  # Replace multiple spaces with a single space
    text = text.strip()  # Remove leading and trailing spaces
    return text

def extract_text_from_pdf(pdf_path):
    resource_manager = PDFResourceManager()
    fake_file_handle = io.StringIO()
    converter = TextConverter(resource_manager, fake_file_handle, laparams=LAParams())
    page_interpreter = PDFPageInterpreter(resource_manager, converter)

    with open(pdf_path, 'rb') as fh:
        for page in PDFPage.get_pages(fh, caching=True, check_extractable=True):
            page_interpreter.process_page(page)
            text = fake_file_handle.getvalue()
            yield text

    converter.close()
    fake_file_handle.close()

@app.route('/')
def upload_form():
    return render_template('upload.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_type = filename.rsplit('.', 1)[1].lower()
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        text_content = parse_resume(filepath)
        age = extract_age(text_content)
        skills = extract_skills(text_content)
        education = extract_education(text_content)
        upload_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        resume_id = store_resume(filename, file_type, upload_date, text_content, age, skills, education)

        # Find suitable jobs
        matched_jobs = find_matching_jobs(resume_id, age, skills, education)
        
        return render_template('display_resume.html', text_content=text_content, age=age, skills=skills, education=education, matched_jobs=matched_jobs)
    else:
        flash('Allowed file types are pdf, doc, docx')
        return redirect(request.url)

def parse_resume(filepath):
    if filepath.endswith('.pdf'):
        return ' '.join(extract_text_from_pdf(filepath))
    elif filepath.endswith('.doc') or filepath.endswith('.docx'):
        return parse_doc(filepath)
    return ''

def parse_doc(filepath):
    document = docx.Document(filepath)
    text = ''
    for para in document.paragraphs:
        text += para.text
    
    # Clean and normalize the text
    return clean_text(text)

def extract_age(text):
    birthdate_patterns = [
        r'\b(?:born|birthdate|dob|date of birth)[\s:]*([A-Za-z]+ \d{1,2}, \d{4})\b',  # Example: January 01, 2003
        r'\b(?:born|birthdate|dob|date of birth)[\s:]*([\d]{1,2}/[\d]{1,2}/[\d]{4})\b',  # Example: 01/01/2003
        r'\b(?:born|birthdate|dob|date of birth)[\s:]*([\d]{4}-[\d]{2}-[\d]{2})\b'  # Example: 2003-01-01
    ]
    
    age_pattern = r'\bAge[\s:]*([0-9]+)\b'  # Example: Age: 21

    # Check for age directly mentioned in the text
    age_match = re.search(age_pattern, text, re.IGNORECASE)
    if age_match:
        return int(age_match.group(1))

    # Check for birthdates and calculate age
    for pattern in birthdate_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            birthdate_str = matches[0]
            try:
                for fmt in ('%B %d, %Y', '%m/%d/%Y', '%Y-%m-%d'):
                    try:
                        birthdate = datetime.strptime(birthdate_str, fmt)
                        today = datetime.today()
                        age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
                        return age
                    except ValueError:
                        continue
            except ValueError:
                return None

    return None

#From skills.txt
def load_skills_from_file(filename):
    try:
        with open(filename, 'r') as file:
            skills = [line.strip() for line in file if line.strip()]
        return skills
    except FileNotFoundError:
        print(f"File {filename} not found.")
        return []

def extract_skills(text):
    skill_list = load_skills_from_file(skills_file_path)
    
    if not skill_list:
        return 'No skills found'
    
    text_lower = text.lower()
    skills_found = [skill for skill in skill_list if skill.lower() in text_lower]

    return ', '.join(skills_found) if skills_found else 'No skills found'

def extract_education(text):
    doc = nlp(text)
    education_info = [ent.text for ent in doc.ents if ent.label_ == 'EDUCATION']
    return ', '.join(education_info) if education_info else 'No education information found'

def store_resume(file_name, file_type, upload_date, text_content, age, skills, education):
    cursor = db.cursor()
    query = """
        INSERT INTO resumes (file_name, file_type, upload_date, text_content, age, skills, education) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """
    cursor.execute(query, (file_name, file_type, upload_date, text_content, age, skills, education))
    resume_id = cursor.lastrowid
    db.commit()
    cursor.close()
    print("Resume stored in database.")
    
    return resume_id

def find_matching_jobs(resume_id, age, skills, education):
    if skills is None:
        skills = 'No skills found'
    if education is None:
        education = 'No education found'
    
    cursor = db.cursor()
    query = "SELECT job_title, job_requirements, job_skills FROM job_descriptions"
    cursor.execute(query)
    jobs = cursor.fetchall()
    cursor.close()

    matched_jobs = []

    for job in jobs:
        job_title, job_requirements, job_skills = job
        skill_matches = [skill for skill in skills.split(', ') if skill.lower() in job_skills.lower()]
        education_matches = [edu for edu in education.split(', ') if edu.lower() in job_requirements.lower()]

        if skill_matches and education_matches:
            matched_jobs.append({
                'job_title': job_title,
                'job_requirements': job_requirements,
                'job_skills': job_skills,
                'skill_matches': ', '.join(skill_matches),
                'education_matches': ', '.join(education_matches)
            })

            # Store each match
            store_job_match(resume_id, job_title)
    
    return matched_jobs

def store_job_match(resume_id, job_title):
    cursor = db.cursor()
    query = """
        INSERT INTO job_matches (resume_id, job_title) 
        VALUES (%s, %s)
    """
    cursor.execute(query, (resume_id, job_title))
    db.commit()
    cursor.close()
    print("Job match stored in database.")

if __name__ == "__main__":
    app.run(debug=True)
