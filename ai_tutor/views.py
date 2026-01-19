from django.shortcuts import render, redirect
from .ai_logic import chat_with_ai


def ai_home(request):

    # Initialize session storage
    if "all_chats" not in request.session:
        request.session["all_chats"] = []

    if "current_chat" not in request.session:
        request.session["current_chat"] = []

    # NEW CHAT clicked
    if "new" in request.GET:
        if request.session.get("current_chat"):
            request.session["all_chats"].append(
                request.session["current_chat"]
            )
            request.session["current_chat"] = []

        request.session.modified = True
        return redirect(request.path)



    # MESSAGE SENT
    if request.method == "POST":
        message = request.POST.get("message")

        if message:
            # User message
            request.session["current_chat"].append({
                "sender": "user",
                "text": message
            })

            # AI reply
            ai_reply = chat_with_ai(message)

            request.session["current_chat"].append({
                "sender": "assistant",
                "text": ai_reply
            })

            request.session.modified = True

    return render(
        request,
        "ai_tutor/input.html",
        {
            "chat_history": request.session["current_chat"],
            "all_chats": request.session["all_chats"]
        }
    )
