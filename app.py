import praw
from pprint import pprint
import threading
import random
import requests
import re
from time import sleep
from prawcore.exceptions import Forbidden, ServerError
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

reddit = praw.Reddit(
    client_id="",
    client_secret="",
    password="",
    user_agent="a bot made to count the pixels on a post",
    username="pixel-counter-bot",
)

active_subreddits = ["countablepixels+countablepixelscirclejerk"]

def addComma(num):
    return '{:,}'.format(num)

bot_statement = "\n\n^(I am a bot. This action was performed automatically.)"

def sortMedia(gallery_data):
    ordered_ids = []
    for item in gallery_data['items']:
        ordered_ids.append(item['id'])
    ordered_ids = sorted(ordered_ids)
    media_ids = []
    for i in ordered_ids:
        for j in gallery_data['items']:
            if(i == j['id']):
                media_ids.append(j['media_id'])
                break
    
    return media_ids

def constructComment(submission, from_mention):
    if hasattr(submission, 'link_flair_text') and vars(submission)['link_flair_text'] == 'no bot':
        if from_mention:
            return "No bot flair detected. Refraining from counting pixels."
        return ""
    elif hasattr(submission, 'link_flair_text') and vars(submission)['link_flair_text'] == 'spoiler':
        spoiler = True
    else:
        spoiler = False
    comment_string = ""
    if hasattr(submission, 'post_hint'):
        hint = submission.post_hint
        if hint == 'image' or hint == 'hosted:video':
            source = vars(submission)['preview']['images'][0]['source']
            x = source['width']
            y = source['height']
            size = x * y
            if size > 1 and random.randint(1, 50) == 50:
                eat = True
                size -= 1
            else:
                eat = False
            comment_string = re.sub(r'\{hint\}', 'video' if hint == 'hosted:video' else 'image', "The {hint} in this post has ")
            comment_string += f"{'>!' if spoiler else ''}{addComma(size)}({addComma(x)}×{addComma(y)}){'!<' if spoiler else ''} pixel{'s' if size > 1 else ''}{'!' if hint != 'hosted:video' else ' per frame'}"
            if hint == 'hosted:video':
                frame_count = vars(submission)['media']['reddit_video']['duration'] * 30
                comment_string += f" and {addComma(frame_count)} frame{'s' if frame_count > 1 else ''} for a total of {addComma(frame_count*size)} pixels!"
            if eat:
                comment_string += "\n\nYou may have noticed that one pixel is missing from that calculation. That is because I stole it. That pixel is mine now, and you're not getting it back."
    elif hasattr(submission, 'media_metadata'):
        try:
            image_list = vars(submission)["media_metadata"]
            if image_list is not None and len(image_list) > 1:
                pixel_total = 0
                comment_string = "This post contains multiple images!\n\n"
                try:
                    media_ids = sortMedia(submission.gallery_data)
                except Exception as e:
                    pprint(vars(submission))
                    pprint(e)
                    return "Oh no! Image sorting could not be completed because Reddit API failed to provide gallery attribute data."
                for i, item in enumerate(media_ids, 1):
                    retry = True
                    fails = 0
                    while retry:
                        if fails <= 6:
                            try:
                                image_source = image_list[item]['s']
                                x = image_source['x']
                                y = image_source['y']
                                retry = False
                            except Exception as e:
                                pprint(e)
                                print("Resolution fetch failed. Retrying...")
                                sleep(5)
                                fails += 1
                        else:
                            print("Resolution fetch failed too many times. Giving up on this post.")
                            return "Whoops! It looks like I am unable to fetch the image data for this post because Reddit failed to process it."
                    comment_string += f"Image {i} has {'>!' if spoiler else ''}{addComma(x * y)}({addComma(x)}×{addComma(y)}){'!<' if spoiler else ''} pixel{'s' if x * y > 1 else ''}.\n\n"
                    pixel_total += x * y
                comment_string += "Total pixels: " + addComma(pixel_total) + "."
            else:
                for image in vars(submission)["media_metadata"]:
                    retry = True
                    fails = 0
                    while retry:
                        if fails <= 6:
                            try:
                                image_source = vars(submission)['media_metadata'][image]['s']
                                x = image_source['x']
                                y = image_source['y']
                                size = x * y
                                comment_string += f"The image in this post has {'>!' if spoiler else ''}{addComma(size)}({addComma(x)}×{addComma(y)}){'!<' if spoiler else ''} pixel{'s' if size > 1 else ''}!"
                                retry = False
                            except Exception as e:
                                pprint(e)
                                print("Resolution fetch failed. Retrying...")
                                sleep(5)
                                fails += 1
                        else:
                            print("Resolution fetch failed too many times. Giving up on this post.")
                            return "Whoops! It looks like I am unable to fetch the image data for this post because Reddit failed to process it."
        except TypeError as e:
            print("Unexpected type error! Cannot process post!")
            pprint(e)
            return "Unexpected error! Error has been automatically reported to my developer."
    elif hasattr(submission, 'crosspost_parent_list'):
        comment_string += constructComment(praw.models.Submission(reddit=reddit, id=vars(submission)['crosspost_parent_list'][0]['id']), from_mention)
    return comment_string

def attemptComment(submission, item, from_mention):
    comment_string = constructComment(submission, from_mention)
    if comment_string is not None and len(comment_string) > 0:
        try:
            if item is not None:
                if random.randint(1, 50) == 50:
                    item.reply(comment_string + bot_statement + "^( You can learn more [here](https://www.youtube.com/watch?v=dQw4w9WgXcQ).)")
                else:
                    item.reply(comment_string + bot_statement)
            else:
                if random.randint(1, 50) == 50:
                    submission.reply(comment_string + bot_statement + "^( You can learn more [here](https://www.youtube.com/watch?v=dQw4w9WgXcQ).)")
                else:
                    submission.reply(comment_string + bot_statement)
            print("Replied to a post!")
        except Forbidden:
            try:
                item.author.message(subject="I was banned.", message=f"It appears that I am banned from r/{submission.subreddit.display_name}, so I am unable to reply to [this comment]({submission.permalink}). The constructed reply is as follows:\n\n{comment_string}" + bot_statement)
            except Forbidden:
                pass
        except Exception as e:
            print("Unexpected error!")
            pprint(e)
    else:
        print("Cannot comment on this post!")

def get_image_resolution(url):
    try:
        response = requests.get(url, stream=True)
        response.raw.decode_content = True
        image = Image.open(BytesIO(response.raw.read(1024)))  # Read only the first 1024 bytes
        return image.size  # returns (width, height)
    except Exception as e:
        print(f"Failed to get image resolution for {url}: {e}")
        return None

def handleItem(submission, item, from_comment):
    retry = True
    while retry:
        try:
            if from_comment and item.parent_id.startswith("t1_"):
                try:
                    soup = BeautifulSoup(item.parent().body_html, features="html.parser")
                    links = [link['href'] for link in soup.find_all('a')]
                    image = None
                    for link in links:
                        if re.findall(r'\.(?:png|jpg|jpeg|gif|webp)', link):
                            image = link.replace('preview', 'i', 1)
                            break
                    if image is None:
                        raise TypeError
                    resolution = get_image_resolution(image)
                    if resolution:
                        width, height = resolution
                        try:
                            item.reply(f"The image in this comment has {addComma(width * height)}({addComma(width)}×{addComma(height)}) pixel{'s' if (width*height) > 1 else ''}!" + bot_statement)
                        except Forbidden:
                            try:
                                item.author.message(subject="I was banned.", message=f"It appears that I am banned from r/{item.subreddit.display_name}, so I am unable to reply to [this comment]({item.context}). The constructed reply is as follows:\n\nThe image in this comment has {addComma(width * height)}({addComma(width)}×{addComma(height)}) pixel{'s' if (width*height) > 1 else ''}!" + bot_statement)
                            except Forbidden:
                                pass
                except TypeError:
                    attemptComment(submission, item, from_comment)
                item.mark_read()
                print("Replied to a comment!")
            else:
                attemptComment(submission, item, from_comment)
            retry = False
        except ServerError:
            print("Server error. Retrying...")
            sleep(5)
            retry = True

def submissionStream():
    for submission in reddit.subreddit("countablepixels").stream.submissions():
        if submission.comments is not None:
            already_commented = False
            for comment in submission.comments:
                if comment.author == "pixel-counter-bot":
                    already_commented = True
                    break
        
        if not already_commented:
            handleItem(submission, None, False)

def mentionStream():
    for item in reddit.inbox.unread(limit=100):
        info = vars(item)
        if item.new and info['type'] == 'username_mention':
            handleItem(item.submission, item, True)
            item.mark_read()

    print("Successfully checked old inbox items.")

    for item in reddit.inbox.stream():
        info = vars(item)
        if item.new and info['type'] == 'username_mention':
            handleItem(item.submission, item, True)
            item.mark_read()



submissionThread = threading.Thread(target = submissionStream)
submissionThread.start()
mentionThread = threading.Thread(target = mentionStream)
mentionThread.start()
