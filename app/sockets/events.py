from flask import request
from flask_socketio import emit
from app import socketio, sessions
from app.config import Config
from app.services.deepseek import generate_with_retry, check_answer_relevance
from app.services.utils import load_interviews, strip_markdown
from app.services.cv_parser import build_cv_context
from app.services.gemini_vision import analyze_frames_batch

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
    cv_text = data.get('cv_text', None)  # Optional: CV text from /api/upload-cv

    if not interview_id:
        emit('error', {'message': 'interview_id is required'})
        return

    interviews = load_interviews()
    selected = next((item for item in interviews if item["id"] == interview_id), None)
    
    if not selected:
        emit('error', {'message': 'Invalid interview_id'})
        return

    print(f"Starting interview '{selected['name']}' for session {request.sid}")

    # Build system prompt — inject CV context if applicable
    system_prompt = selected["system_prompt"]
    has_cv = False

    if cv_text and selected.get("requires_cv", False):
        # RAG: Inject CV context into the system prompt
        cv_context = build_cv_context(cv_text)
        system_prompt = system_prompt + cv_context
        has_cv = True
        print(f"CV context injected ({len(cv_text)} chars) for '{selected['name']}'")
    elif selected.get("requires_cv", False) and not cv_text:
        print(f"Interview '{selected['name']}' supports CV but none was provided. Proceeding without CV.")
    else:
        print(f"Interview '{selected['name']}' does not require CV. Skipping CV injection.")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": "Please begin the interview."}
    ]

    # Generate first question
    first_question = generate_with_retry(messages)
    messages.append({"role": "assistant", "content": first_question})

    # Save session state (with new fields for CV and frames)
    sessions[request.sid] = {
        'messages': messages,
        'question_count': 1,
        'selected_interview': selected,
        'cv_text': cv_text if has_cv else None,
        'has_cv': has_cv,
        'frames': [],  # Collected webcam frames (base64)
    }

    emit('question', {
        'question_number': 1,
        'text': first_question,
        'clean_text': strip_markdown(first_question),
        'is_finished': False,
        'has_cv': has_cv,
        'requires_cv': selected.get("requires_cv", False)
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

    # Check if the answer is relevant
    is_relevant = check_answer_relevance(session['messages'], answer)

    if not is_relevant:
        warning_msg = "Please stay on topic and answer the interview question."
        session['messages'].append({"role": "user", "content": answer})
        session['messages'].append({"role": "assistant", "content": warning_msg})
        emit('question', {
            'question_number': session['question_count'],
            'text': warning_msg,
            'clean_text': warning_msg,
            'is_finished': False
        })
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

@socketio.on('receive_frame')
def handle_receive_frame(data):
    """
    Receive a webcam frame from the frontend for behavioral analysis.
    Frames are stored in the session and analyzed in batch at the end.
    """
    if request.sid not in sessions:
        # Silently ignore frames if no active session
        return

    session = sessions[request.sid]
    frame_data = data.get('frame_data', None)

    if not frame_data:
        return

    # Cap the number of stored frames to avoid memory issues
    if len(session['frames']) < Config.MAX_FRAMES_STORED:
        session['frames'].append(frame_data)
        print(f"Frame {len(session['frames'])} captured for session {request.sid}")
    
    # Acknowledge receipt
    emit('frame_received', {
        'frame_count': len(session['frames']),
        'max_frames': Config.MAX_FRAMES_STORED
    })

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

    # --- Behavioral Analysis (if frames were captured) ---
    behavioral_summary = None
    frames = session.get('frames', [])
    
    if frames and len(frames) > 0:
        print(f"Analyzing {len(frames)} webcam frames for behavioral assessment...")
        try:
            behavioral_summary = analyze_frames_batch(frames)
            print(f"Behavioral analysis completed ({len(behavioral_summary)} chars)")
        except Exception as e:
            print(f"Behavioral analysis failed: {e}")
            behavioral_summary = "Behavioral analysis could not be completed due to a technical error."
    
    # Combine DeepSeek interview report + Gemini behavioral analysis
    combined_report = report
    if behavioral_summary:
        combined_report = report + "\n\n" + "=" * 60 + "\n\n" + \
            "## 📹 VIDEO BEHAVIORAL ANALYSIS\n" + \
            "(Powered by AI Video Analysis)\n\n" + \
            behavioral_summary

    # Extract the Final Remarks to be spoken aloud
    spoken_remarks = "The interview has concluded. Here is your evaluation report."
    import re
    # Look for any variation of "Final...Remarks" and capture everything after it
    match = re.search(r'Final.*?Remarks:?\s*(.*)', combined_report, re.IGNORECASE | re.DOTALL)
    if match:
        extracted = match.group(1).strip()
        # Clean it up: remove markdown or trailing lines if needed
        # Just taking the first paragraph is usually safest
        first_paragraph = extracted.split('\n')[0].strip()
        if first_paragraph:
            # Strip markdown bolding
            spoken_remarks = strip_markdown(first_paragraph)

    emit('report', {
        'text': combined_report,
        'clean_text': strip_markdown(combined_report),
        'spoken_remarks': spoken_remarks,
        'is_finished': True,
        'has_behavioral_analysis': behavioral_summary is not None,
        'frames_analyzed': len(frames)
    })

    # Clean up session
    if sid in sessions:
        del sessions[sid]
