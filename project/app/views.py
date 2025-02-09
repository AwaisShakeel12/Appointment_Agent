from django.shortcuts import render
from .Agents1 import app
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync

@csrf_exempt
def home(request):
    if 'conversation' not in request.session:
        request.session['conversation'] = []

    conversation = request.session['conversation']

    if request.method == 'POST':
        user_msg = request.POST.get('user_msg', '')

        conversation.append({'sender': 'User', 'message': user_msg})

        initial_input = {'messages': [user_msg]}
        thread_data = {'configurable': {'thread_id': '1'}}  

        response = async_to_sync(get_ai_response)(initial_input, thread_data)

        if response:
            conversation.append({'sender': 'AI', 'message': response})

        request.session['conversation'] = conversation
        request.session.modified = True  

    return render(request, 'ai.html', {'conversation': conversation})


async def get_ai_response(initial_input, thread_data):
    ai_response = ""
    async for event in app.astream(initial_input, thread_data, stream_mode='values'):
        message = event['messages'][-1]
        if hasattr(message, 'additional_kwargs') and 'tool_calls' in message.additional_kwargs:
            continue
        ai_response = message.content
    return ai_response


