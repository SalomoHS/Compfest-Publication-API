import json
from mutagen import File
from .supabaseClient import supabase
from .elevenlabsClient import *
from langchain_core.messages import AIMessage
from langchain_mcp_adapters.client import MultiServerMCPClient
from .scrapeTools import summarize_news
import asyncio
from io import BytesIO
import requests
import uuid

async def get_scrape_tools():
    mcp_client = MultiServerMCPClient(
        {
            "detik": {
                "transport": "streamable_http",
                "url": os.getenv("MCP_SERVER")
            },
        }
    )
    scrape_tools = await mcp_client.get_tools()
    scrape_tools.append(summarize_news)

    return scrape_tools

async def update_state_news_metadata(state):
    return {
        "news_title":state['parsed_ai_response']['news_title'], 
        "news_summary":state['parsed_ai_response']['news_summary'],
        "latest_news_url":state['parsed_ai_response']['news_url']
    }

async def json_parser(state):
    """
    Get parsed ai response from 'messages' table
    Returns:
        dict: A dictionary of containing parsed ai response

    Example:
    >>> [{'speakerId': 'id1', 'speakerName': 'Budi Santoso'},
        {'speakerId': 'id2', 'speakerName': 'Doni Kusuma'}]
    """
    ai_response = None
    for msg in state["messages"]:
        if isinstance(msg, AIMessage):
            ai_response = msg
    print(ai_response)

    temp = ai_response.content\
            .replace("```json","")\
            .replace("```","")\
            .strip()
    temp = json.loads(temp)
    return {"parsed_ai_response": temp}

async def get_speakers():
    """
    Get speaker data from 'Speakers' table
    Returns:
        list: A list of dictionaries containing speaker data
    Example:
    >>> [{'speakerId': 'id1', 'speakerName': 'Budi Santoso'},
        {'speakerId': 'id2', 'speakerName': 'Doni Kusuma'}]
    """
    return supabase\
            .table("Speakers")\
            .select("*")\
            .execute().data

async def get_topics():
    """
    Get topic data from 'Topics' table
    Returns:
        list: A list of dictionaries containing topic data
    Example:
    >>> [{'topicId': 'MOVE', 'topicName': 'Transportation'},
        {'topicId': 'TECH', 'topicName': 'Technology'}]
    """
    return supabase\
            .table("Topics")\
            .select("*")\
            .execute().data

async def insert_podcast(state):
    try:    

        speaker1Id = supabase\
            .table("Speakers")\
            .select("speakerId")\
            .eq("speakerName", state["speakers"][0])\
            .execute()
        
        speaker2Id = supabase\
            .table("Speakers")\
            .select("speakerId")\
            .eq("speakerName", state["speakers"][1])\
            .execute()

        supabase\
            .table("Podcasts")\
            .insert({
                'podcastId': state["parsed_ai_response"]['Insert_Podcasts']['podcastId'],
                'topicId': state["parsed_ai_response"]['Insert_Podcasts']['topicId'],
                'audio': state["result_url"],
                'duration': state["podcast_duration"],
                'title': state["news_title"],
                'language':state["language"],
                'speaker1':speaker1Id.data[0]['speakerId'],
                'speaker2':speaker2Id.data[0]['speakerId'],
                'city':state['location'],
                'timezone':"WIB",
            })\
            .execute()

    except Exception as e: #podcastId exists
        print(e)
        speaker1Id = supabase\
            .table("Speakers")\
            .select("speakerId")\
            .eq("speakerName", state["speakers"][0])\
            .execute()
        
        speaker2Id = supabase\
            .table("Speakers")\
            .select("speakerId")\
            .eq("speakerName", state["speakers"][1])\
            .execute()
        max_retries = 3
        attempt = 0
        for _ in range(max_retries):
            pod_id = f"POD-{uuid.uuid4().hex[:12]}"
            state["parsed_ai_response"]['Insert_Podcasts']['podcastId'] = pod_id

            try:
                supabase\
                .table("Podcasts")\
                .insert({
                    'podcastId': state["parsed_ai_response"]['Insert_Podcasts']['podcastId'],
                    'topicId': state["parsed_ai_response"]['Insert_Podcasts']['topicId'],
                    'audio': state["result_url"],
                    'duration': state["podcast_duration"],
                    'title': state["news_title"],
                    'language':state["language"],
                    'speaker1':speaker1Id.data[0]['speakerId'],
                    'speaker2':speaker2Id.data[0]['speakerId'],
                    'city':state['location'],
                    'timezone':"WIB",
                }).execute()

                for _,dialog in enumerate(state["parsed_ai_response"]['Insert_Dialogs']):
                    old_dialog_id = dialog["dialogId"]
                    suffix = old_dialog_id.split("-")[-1]  # get number suffix
                    dialog["dialogId"] = f"{pod_id}-{suffix}"
                    dialog["podcastId"] = pod_id

                break
            except Exception as e:
                attempt += 1
                continue

        if attempt == max_retries:
            raise Exception(f"Could not insert to 'Podcasts' table: {state['parsed_ai_response']['Insert_Podcasts']['podcastId']} already exist")

def insert_conversation(state):
    supabase\
        .table("Conversations")\
        .insert(state["parsed_ai_response"]['Insert_Dialogs'])\
        .execute()

async def delete_voices(client_num:str):
    api = [
        os.environ['ELEVENLABS_KEY_11'],
        os.environ['ELEVENLABS_KEY_1'],
        os.environ['ELEVENLABS_KEY_2'],
        os.environ['ELEVENLABS_KEY_3'],
        os.environ['ELEVENLABS_KEY_4'],
        os.environ['ELEVENLABS_KEY_5'],
    ]

    toBeDelete = api[client_num]
    try:
        res = requests.get("https://api.elevenlabs.io/v2/voices",headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
            "xi-api-key": toBeDelete,
            "Content-Type": "application/json",
        })

        for voice in res.json()['voices'][:3]:
            delete = requests.delete(f"https://api.elevenlabs.io/v1/voices/{voice['voice_id']}",headers={
                "xi-api-key": toBeDelete,
                "Content-Type": "application/json",
            })
        
        print("DELETE VOICES")

    except Exception as e:
        raise Exception("Could not delete voices")

async def generate_dialog(state):
    speakers = list(map(lambda x: x['speakerId'],state["parsed_ai_response"]['Insert_Dialogs']))
    dialogs = list(map(lambda x: x['dialog'],state["parsed_ai_response"]['Insert_Dialogs']))
    # print("speaker: ",speaker)
    clients = [
        elevenlabs_client_11,elevenlabs_client_5,elevenlabs_client_1, elevenlabs_client_2, 
        elevenlabs_client_3,elevenlabs_client_4
    ]

    clients_str = ["elevenlabs_client_11","elevenlabs_client_5","elevenlabs_client_1", "elevenlabs_client_2", "elevenlabs_client_3", "elevenlabs_client_4"]

    error_state = {
        "elevenlabs_client_1": '', 
        "elevenlabs_client_2": '', 
        "elevenlabs_client_3": '',
        "elevenlabs_client_4": '',
        "elevenlabs_client_5":'',
        "elevenlabs_client_11":'',
    }

    
    
    attempt = 0
    while attempt < len(clients):
        try:
            request_ids = []
            audio_buffers = []

            for paragraph, speaker in zip(dialogs, speakers):
                limited_request_ids = request_ids[-3:]
                with clients[attempt].text_to_speech.with_raw_response.convert(
                    text=paragraph,
                    voice_id=speaker,
                    model_id="eleven_multilingual_v2",
                    previous_request_ids=limited_request_ids
                ) as response:
                    request_ids.append(response._response.headers.get("request-id"))
                    audio_data = b''.join(chunk for chunk in response.data)
                    audio_buffers.append(BytesIO(audio_data))

            # # Combine audio
            combined_stream = BytesIO(b''.join(buffer.getvalue() for buffer in audio_buffers))
            combined_stream.seek(0)  # important!
            audio = File(combined_stream)
            duration = int(round(audio.info.length))  

            minutes = duration // 60
            seconds = duration % 60

            formatted_duration = f"{minutes:.0f}:{seconds:02d}"

        
            
            file_name = state["parsed_ai_response"]['Insert_Podcasts']['podcastId'] + "/fullPodcast.mp3"

            supabase\
                .storage.from_("podcast")\
                .upload(file_name, combined_stream.getvalue(), {
                    "content-type": "audio/mpeg",  # Tell Supabase it's an audio file
                })
            # # save(combined_stream, "test1.mp3")
            storage = supabase.storage.from_("podcast").get_public_url(file_name)
            return {"result_url": storage, "podcast_duration": formatted_duration}


        except Exception as e:
            client_name = clients_str[attempt]
            error_state[client_name] = str(e)
            attempt+=1
            continue
    delete_voices(attempt)
    

    if attempt == len(clients):
        raise Exception("Could not generate audio: Please check API keys")

async def make_audio_hooks(state):
    audio_stream = elevenlabs_client_11.text_to_speech.convert(
        text=state["parsed_ai_response"]['Tiktok_Hooks']['text'],
        voice_id=state["parsed_ai_response"]['Tiktok_Hooks']['speakerId'],
        model_id="eleven_multilingual_v2",
        output_format="mp3_44100_128",
    )

    audio_bytes = b"".join(audio_stream)

    combined_stream = BytesIO(audio_bytes)
    combined_stream.seek(0)
    file_name = state["parsed_ai_response"]['Insert_Podcasts']['podcastId'] + "/hooks.mp3"
    supabase\
        .storage.from_("podcast")\
        .upload(file_name, combined_stream.getvalue(), {
            "content-type": "audio/mpeg",  
        })
   
    storage = supabase.storage.from_("podcast").get_public_url(file_name)
    return {'hooks_audio': storage}

async def create_video(state):
    data = {
        "id": "21aafac1-edfd-48e9-abcd-b30f76b9fccd",
        "merge": [
        {
        "find": "NEWS_TITLE",
        "replace": state['news_title']
        },
        {
        "find": "AUDIO",
        "replace": state['hooks_audio']
        }
    ]
    }
    data_to_json= json.dumps(data)
    render = requests.post("https://api.shotstack.io/v1/templates/render",data=data_to_json,headers={
        "Content-Type":"application/json",
        "x-api-key":os.environ['SHOTSTACK']
    })
    render_response = render.json()
    
    while True:
        poll = requests.get(f"https://api.shotstack.io/edit/v1/render/{render_response['response']['id']}",headers={
            "Content-Type":"application/json",
            "x-api-key":os.environ['SHOTSTACK']
        })
        poll_response = poll.json()
        isComplete = poll_response['response']['status']

        if isComplete == "done":
            get_url = poll_response['response']['url']
            resp = requests.get(get_url)
            file_data = resp.content

            file_name = state["parsed_ai_response"]['Insert_Podcasts']['podcastId'] + '/video.mp4'

            supabase.storage.from_("podcast").upload(file_name,file_data,{
                "content-type":"video/mp4"
            })
            video_file = supabase.storage.from_("podcast").get_public_url(file_name)

            supabase\
            .table("Podcasts")\
                .update({'video':video_file})\
                .eq('podcastId',state["parsed_ai_response"]['Insert_Podcasts']['podcastId'])\
                .execute()

            return {'video_url': video_file}

        await asyncio.sleep(5)

async def upload_to_tiktok(state):
    res = requests.get(os.getenv("MAKE_WEBHOOKS"))
    return {'request_to_make': str(res.status_code)}