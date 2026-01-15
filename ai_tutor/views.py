from django.shortcuts import render
from django.core.files.storage import FileSystemStorage

def ai_home(request):
    response = None
    image_url = None
    follow_up = None   # ✅ important

    if request.method == "POST":
        question = request.POST.get("question")
        image = request.FILES.get("image")

        if image:
            fs = FileSystemStorage()
            filename = fs.save(image.name, image)
            image_url = fs.url(filename)

            response = (
                "I see you uploaded an image. "
                "This image seems related to your question. "
                "Here is a simple explanation based on what a teacher would say."
            )
            follow_up = "What do you think is the most important part of this image?"

        elif question:
            response = (
                f"Let me explain this step by step: {question} is an important topic. "
                "Here is a simple explanation."
            )
            follow_up = "Can you explain this concept in your own words?"

    return render(
        request,
        "ai_tutor/input.html",
        {
            "response": response,
            "image_url": image_url,
            "follow_up": follow_up
        }
    )
