"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

import json
from copy import deepcopy
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

app = FastAPI(
    title="Mergington High School API",
    description="API for viewing and signing up for extracurricular activities",
)

current_dir = Path(__file__).parent
static_dir = current_dir / "static"
data_dir = current_dir / "data"
activities_file = data_dir / "activities.json"
students_file = data_dir / "students.json"
state_lock = Lock()


DEFAULT_ACTIVITIES = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"],
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"],
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"],
    },
    "Soccer Team": {
        "description": "Join the school soccer team and compete in matches",
        "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
        "max_participants": 22,
        "participants": ["liam@mergington.edu", "noah@mergington.edu"],
    },
    "Basketball Team": {
        "description": "Practice and play basketball with the school team",
        "schedule": "Wednesdays and Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["ava@mergington.edu", "mia@mergington.edu"],
    },
    "Art Club": {
        "description": "Explore your creativity through painting and drawing",
        "schedule": "Thursdays, 3:30 PM - 5:00 PM",
        "max_participants": 15,
        "participants": ["amelia@mergington.edu", "harper@mergington.edu"],
    },
    "Drama Club": {
        "description": "Act, direct, and produce plays and performances",
        "schedule": "Mondays and Wednesdays, 4:00 PM - 5:30 PM",
        "max_participants": 20,
        "participants": ["ella@mergington.edu", "scarlett@mergington.edu"],
    },
    "Math Club": {
        "description": "Solve challenging problems and participate in math competitions",
        "schedule": "Tuesdays, 3:30 PM - 4:30 PM",
        "max_participants": 10,
        "participants": ["james@mergington.edu", "benjamin@mergington.edu"],
    },
    "Debate Team": {
        "description": "Develop public speaking and argumentation skills",
        "schedule": "Fridays, 4:00 PM - 5:30 PM",
        "max_participants": 12,
        "participants": ["charlotte@mergington.edu", "henry@mergington.edu"],
    },
}


def build_student_records(activities):
    students = {}

    for activity_name, details in activities.items():
        for email in details.get("participants", []):
            record = students.setdefault(email, {"email": email, "activities": []})
            if activity_name not in record["activities"]:
                record["activities"].append(activity_name)

    return dict(sorted(students.items()))


def load_json_file(file_path, default_value):
    if not file_path.exists():
        return deepcopy(default_value)

    with file_path.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def save_json_file(file_path, data):
    with file_path.open("w", encoding="utf-8") as file_handle:
        json.dump(data, file_handle, indent=2, sort_keys=True)
        file_handle.write("\n")


def normalize_student_records(students_data, activities_data):
    normalized_students = {}

    for email, record in students_data.items():
        normalized_record = dict(record)
        normalized_record["email"] = email
        normalized_record["activities"] = [
            activity_name
            for activity_name, activity_details in activities_data.items()
            if email in activity_details.get("participants", [])
        ]
        normalized_students[email] = normalized_record

    for activity_name, activity_details in activities_data.items():
        for email in activity_details.get("participants", []):
            record = normalized_students.setdefault(
                email,
                {"email": email, "activities": []},
            )
            if activity_name not in record["activities"]:
                record["activities"].append(activity_name)

    return dict(sorted(normalized_students.items()))


def load_app_state():
    data_dir.mkdir(exist_ok=True)

    activities_data = load_json_file(activities_file, DEFAULT_ACTIVITIES)
    students_data = load_json_file(students_file, build_student_records(activities_data))
    students_data = normalize_student_records(students_data, activities_data)

    save_json_file(activities_file, activities_data)
    save_json_file(students_file, students_data)

    return activities_data, students_data


# Mount the static files directory
app.mount("/static", StaticFiles(directory=static_dir), name="static")


activities, students = load_app_state()


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")


@app.get("/activities")
def get_activities():
    return activities


@app.get("/students")
def get_students():
    return students


@app.get("/students/{email}")
def get_student(email: str):
    if email not in students:
        raise HTTPException(status_code=404, detail="Student not found")

    return students[email]


def persist_state():
    save_json_file(activities_file, activities)
    save_json_file(students_file, students)


def enroll_student_in_activity(activity_name, email):
    activity = activities[activity_name]
    participant_list = activity["participants"]

    if email in participant_list:
        raise HTTPException(status_code=400, detail="Student is already signed up")

    participant_list.append(email)

    student_record = students.setdefault(email, {"email": email, "activities": []})
    if activity_name not in student_record["activities"]:
        student_record["activities"].append(activity_name)


def remove_student_from_activity(activity_name, email):
    activity = activities[activity_name]
    participant_list = activity["participants"]

    if email not in participant_list:
        raise HTTPException(
            status_code=400,
            detail="Student is not signed up for this activity",
        )

    participant_list.remove(email)

    student_record = students.get(email)
    if student_record is not None and activity_name in student_record["activities"]:
        student_record["activities"].remove(activity_name)


@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    with state_lock:
        if activity_name not in activities:
            raise HTTPException(status_code=404, detail="Activity not found")

        enroll_student_in_activity(activity_name, email)
        persist_state()

    return {"message": f"Signed up {email} for {activity_name}"}


@app.delete("/activities/{activity_name}/unregister")
def unregister_from_activity(activity_name: str, email: str):
    """Unregister a student from an activity"""
    with state_lock:
        if activity_name not in activities:
            raise HTTPException(status_code=404, detail="Activity not found")

        remove_student_from_activity(activity_name, email)
        persist_state()

    return {"message": f"Unregistered {email} from {activity_name}"}
