import os
import MySQLdb
from app import app

def get_stored_resumes():
    db = MySQLdb.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        passwd=app.config['MYSQL_PASSWORD'],
        db=app.config['MYSQL_DB']
    )
    cursor = db.cursor()
    query = "SELECT id, file_name FROM resumes"
    cursor.execute(query)
    resumes = cursor.fetchall()
    cursor.close()
    db.close()
    return resumes

def get_job_matches():
    db = MySQLdb.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        passwd=app.config['MYSQL_PASSWORD'],
        db=app.config['MYSQL_DB']
    )
    cursor = db.cursor()
    query = "SELECT resume_id, job_title FROM job_matches"
    cursor.execute(query)
    matches = cursor.fetchall()
    cursor.close()
    db.close()
    return matches

def get_job_descriptions():
    db = MySQLdb.connect(
        host=app.config['MYSQL_HOST'],
        user=app.config['MYSQL_USER'],
        passwd=app.config['MYSQL_PASSWORD'],
        db=app.config['MYSQL_DB']
    )
    cursor = db.cursor()
    query = "SELECT job_title, job_requirements, job_skills FROM job_descriptions"
    cursor.execute(query)
    jobs = cursor.fetchall()
    cursor.close()
    db.close()
    return jobs

def calculate_accuracy(true_values, predicted_values):
    true_set = set(true_values)
    predicted_set = set(predicted_values)
    
    true_positive = len(true_set & predicted_set)
    false_positive = len(predicted_set - true_set)
    false_negative = len(true_set - predicted_set)

    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) > 0 else 0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) > 0 else 0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0

    return {"precision": precision, "recall": recall, "f1_score": f1}

def test_job_matching_accuracy():
    stored_resumes = get_stored_resumes()
    job_matches = get_job_matches()
    job_descriptions = get_job_descriptions()
    
    # Map resume_id to matched jobs
    resume_to_jobs = {}
    for resume_id, job_title in job_matches:
        if resume_id not in resume_to_jobs:
            resume_to_jobs[resume_id] = set()
        resume_to_jobs[resume_id].add(job_title)

    # Generate expected matches based on job descriptions
    expected_matches = generate_expected_matches(stored_resumes, job_descriptions)

    # Compare and calculate accuracy
    true_matches = []
    predicted_matches = []

    for resume_id, expected_jobs in expected_matches.items():
        true_matches.extend(expected_jobs)
        predicted_jobs = resume_to_jobs.get(resume_id, [])
        predicted_matches.extend(predicted_jobs)

    metrics = calculate_accuracy(true_matches, predicted_matches)
    
    print(f"Job Metrics: {metrics}")

def generate_expected_matches(stored_resumes, job_descriptions):
    expected_matches = {}

    for resume_id, filename in stored_resumes:
        # Fetch resume content to match against job descriptions
        resume_content = get_resume_content(filename)

        # For each resume, determine which jobs are expected to match
        matching_jobs = set()
        for job_title, job_requirements, job_skills in job_descriptions:
            if any(skill.lower() in resume_content.lower() for skill in job_skills.split(',')) or \
               any(req.lower() in resume_content.lower() for req in job_requirements.split(',')):
                matching_jobs.add(job_title)

        expected_matches[resume_id] = matching_jobs

    return expected_matches

def get_resume_content(filename):
    filepath = os.path.abspath(os.path.join(app.config['UPLOAD_FOLDER'], filename))
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as file:
                return file.read()
        except UnicodeDecodeError:
            # Fallback to a different encoding if UTF-8 fails
            try:
                with open(filepath, 'r', encoding='latin-1') as file:
                    return file.read()
            except Exception as e:
                print(f"Error reading file {filepath}: {e}")
                return ""
    return ""


if __name__ == "__main__":
    test_job_matching_accuracy()
