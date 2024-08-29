import os
import MySQLdb
from app import parse_resume, extract_age, extract_skills, extract_education, app

def get_stored_resumes():
    db = MySQLdb.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        passwd=app.config['MYSQL_PASSWORD'],
        db=app.config['MYSQL_DB']
    )
    cursor = db.cursor()
    query = "SELECT file_name, age, skills, education FROM resumes"
    cursor.execute(query)
    resumes = cursor.fetchall()
    cursor.close()
    db.close()
    return resumes

from sklearn.metrics import precision_score, recall_score, f1_score

def calculate_metrics(true_values, predicted_values, average='micro'):
    true_values = [val for val in true_values if val is not None]
    predicted_values = [val for val in predicted_values if val is not None]

    if not true_values or not predicted_values:
        return {"precision": 0, "recall": 0, "f1_score": 0}

    precision = precision_score(true_values, predicted_values, average=average)
    recall = recall_score(true_values, predicted_values, average=average)
    f1 = f1_score(true_values, predicted_values, average=average)

    return {"precision": precision, "recall": recall, "f1_score": f1}


def test_resume_parsing():
    stored_resumes = get_stored_resumes()
    
    true_ages = []
    predicted_ages = []
    true_skills = []
    predicted_skills = []
    true_education = []
    predicted_education = []

    for resume in stored_resumes:
        filename, true_age, true_skills_str, true_education_str = resume
        filepath = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        # Check if file exists before processing
        if not os.path.exists(filepath):
            print(f"File not found: {filepath}")
            continue

        text_content = parse_resume(filepath)
        predicted_age = extract_age(text_content)
        predicted_skills_str = extract_skills(text_content)
        predicted_education_str = extract_education(text_content)

        true_ages.append(true_age)
        predicted_ages.append(predicted_age)
        true_skills.append(true_skills_str)
        predicted_skills.append(predicted_skills_str)
        true_education.append(true_education_str)
        predicted_education.append(predicted_education_str)

    age_metrics = calculate_metrics(true_ages, predicted_ages)
    skills_metrics = calculate_metrics(true_skills, predicted_skills)
    education_metrics = calculate_metrics(true_education, predicted_education)

    return age_metrics, skills_metrics, education_metrics

if __name__ == "__main__":
    age_metrics, skills_metrics, education_metrics = test_resume_parsing()
    print(f"Age extraction metrics: {age_metrics}")
    print(f"Skills extraction metrics: {skills_metrics}")
    print(f"Education extraction metrics: {education_metrics}")
