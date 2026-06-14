from flask import request
from flask_socketio import emit
from app import socketio, sessions
from app.config import Config
from app.services.deepseek import generate_with_retry
from app.services.utils import load_interviews, strip_markdown

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")
    if request.sid in sessions:
        del sessions[request.sid]

@socketio.on('start_interview')
def handle_start_interview(data):
    interview_id = data.get('interview_id')
    if not interview_id:
        emit('error', {'message': 'interview_id is required'})
        return

    interviews = load_interviews()
    selected = next((item for item in interviews if item["id"] == interview_id), None)
    
    if not selected:
        emit('error', {'message': 'Invalid interview_id'})
        return

    print(f"Starting interview '{selected['name']}' for session {request.sid}")

    messages = [
        {"role": "system", "content": selected["system_prompt"]},
        {"role": "user", "content": "Please begin the interview."}
    ]

    # Generate first question
    first_question = generate_with_retry(messages)
    messages.append({"role": "assistant", "content": first_question})

    # Save session state
    sessions[request.sid] = {
        'messages': messages,
        'question_count': 1,
        'selected_interview': selected
    }

    emit('question', {
        'question_number': 1,
        'text': first_question,
        'clean_text': strip_markdown(first_question),
        'is_finished': False
    })

@socketio.on('answer')
def handle_answer(data):
    if request.sid not in sessions:
        emit('error', {'message': 'Session not found. Please start an interview first.'})
        return

    session = sessions[request.sid]
    answer = data.get('answer', '').strip()
    
    if not answer:
        emit('error', {'message': 'Answer cannot be empty'})
        return

    # Check for early exit
    if answer.lower() in ("quit", "exit", "stop"):
        session['messages'].append({"role": "user", "content": answer})
        generate_report(request.sid)
        return

    # Append user's answer
    session['messages'].append({"role": "user", "content": answer})

    if session['question_count'] < Config.MAX_QUESTIONS:
        # Generate next question
        next_question = generate_with_retry(session['messages'])
        session['messages'].append({"role": "assistant", "content": next_question})
        session['question_count'] += 1

        emit('question', {
            'question_number': session['question_count'],
            'text': next_question,
            'clean_text': strip_markdown(next_question),
            'is_finished': False
        })
    else:
        # Reached limit, generate report
        generate_report(request.sid)

def generate_report(sid):
    session = sessions[sid]
    session['messages'].append({
        "role": "user",
        "content": """
INTERVIEW_FINISHED

Generate detailed evaluation report.

Include all scoring criteria and
provide a comprehensive assessment
with improvement plan and final remarks.
"""
    })

    print(f"Generating report for session {sid}...")
    report = generate_with_retry(session['messages'])

    emit('report', {
        'text': report,
        'clean_text': strip_markdown(report),
        'is_finished': True
    })

    # Clean up session
    if sid in sessions:
        del sessions[sid]
