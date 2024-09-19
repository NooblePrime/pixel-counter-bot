import praw
from pprint import pprint
import threading
import random
from time import sleep
from prawcore.exceptions import Forbidden
from prawcore.exceptions import ServerError

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

def checkIfVisited(id):
    file = open('visited_posts.txt', 'r')
    data = file.read()
    file.close()
    return id in data

def logVisit(id):
    file = open('visited_posts.txt', 'a')
    file.write(id + "\n")

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
            comment_string += "The "
            if hint == 'hosted:video':
                comment_string += "video"
            else:
                comment_string += "image"
            size = x * y
            if size > 1 and random.randint(1, 50) == 50:
                eat = True
                size -= 1
            else:
                eat = False
            if spoiler:
                comment_string += f" in this **POST** has >!{addComma(size)}({addComma(x)}×{addComma(y)})!< pixel"
            else:
                comment_string += f" in this **POST** has {addComma(size)}({addComma(x)}×{addComma(y)}) pixel"
                
            if size > 1:
                comment_string += "s"
            if hint == 'hosted:video':

                eat = False
                frame_count = vars(submission)['media']['reddit_video']['duration']*30
                if spoiler:
                    comment_string += f" per frame and an estimated >!{(frame_count)}!< frames"
                else:
                    comment_string += f" per frame and an estimated {(frame_count)} frames"
            comment_string += "!"
            if hint == 'hosted:video':
                if spoiler:
                    comment_string += f"\n\nTotal pixels in video: >!{addComma(size*frame_count)}!<"
                else:
                    comment_string += f"\n\nTotal pixels in video: {addComma(size*frame_count)}"
            if eat:
                comment_string += "\n\nYou may have noticed that one pixel is missing from that calculation. That is because I stole it. That pixel is mine now, and you're not getting it back."
            
    elif hasattr(submission, 'media_metadata'):
            try:
                image_list = vars(submission)["media_metadata"]
                if len(image_list) > 1:
                    pixel_total = 0
                    comment_string += "This post contains multiple images!\n\n"
                    i = 1
                    try:
                        media_ids = sortMedia(submission.gallery_data)
                    except Exception as e:
                        pprint(vars(submission))
                        pprint(e)
                        return "Oh no! Image sorting could not be completed because Reddit API failed to provide gallery attribute data."
                    for item in media_ids:
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
                        if spoiler:
                            comment_string += f"Image {i} has >!{addComma(x * y)}({addComma(x)}×{addComma(y)})!< pixel"
                        else:
                            comment_string += f"Image {i} has {addComma(x * y)}({addComma(x)}×{addComma(y)}) pixel"
                        if x * y > 1:
                            comment_string += "s"
                        
                        comment_string += ".\n\n"
                        pixel_total += x * y
                        i += 1
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
                                    if spoiler:
                                        comment_string += f"This image has >!{addComma(size)}({addComma(x)}×{addComma(y)})!< pixel"
                                    else:
                                        comment_string += f"This image has {addComma(size)}({addComma(x)}×{addComma(y)}) pixel"

                                    if size > 1:
                                        comment_string += "s"
                                    comment_string += "!"
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
        comment_string += constructComment(praw.models.Submission(reddit = reddit, id = vars(submission)['crosspost_parent_list'][0]['id']), from_mention)
    return comment_string


def attemptComment(submission, item, from_mention):
    
    comment_string = constructComment(submission, from_mention)
    if len(comment_string) > 0:
        try:
            if item != None:
                if random.randint(1, 50) == 50:
                    item.reply(comment_string + bot_statement+ "^( You can learn more [here](https://www.youtube.com/watch?v=dQw4w9WgXcQ).)")
                else:
                    item.reply(comment_string + bot_statement)
            else:
                if random.randint(1, 50) == 50:
                    submission.reply(comment_string + bot_statement+ "^( You can learn more [here](https://www.youtube.com/watch?v=dQw4w9WgXcQ).)")
                else:
                    submission.reply(comment_string + bot_statement)
            print("Replied to a post!")
        except Forbidden:
            print("Cannot comment on banned subreddit.")
        except Exception as e:
            print("Unexpected error!")
            pprint(e)
    else:
        print("Cannot comment on this post!")

def submissionStream():
    for submission in reddit.subreddit("countablepixels").stream.submissions():
        retry = True
        while retry:
            try:
                if not checkIfVisited(vars(submission)['id']):
                    attemptComment(submission, None, False)
                    logVisit(vars(submission)['id'])
                retry = False
            except ServerError:
                sleep(5)
                retry = True

def mentionStream():
    retry = True
    while retry:
        try:
            for item in reddit.inbox.unread(limit=100):
                info = vars(item)
                if item.new and info['type'] == 'username_mention':
                    attemptComment(item.submission, item, True)
                    item.mark_read()
            retry = False
        except ServerError:
            print("Server error. Retrying...")
            sleep(5)
            retry = True
    
    print("Successfully checked old inbox items.")

    retry = True
    while retry:
        try:
            for item in reddit.inbox.stream():
                info = vars(item)
                if item.new and info['type'] == 'username_mention':
                    attemptComment(item.submission, item, True)
                    item.mark_read()
            retry = False
        except ServerError:
            print("Server error. Retrying...")
            sleep(5)
            retry = True

print("Startup successful.")

submissionThread = threading.Thread(target = submissionStream)
submissionThread.start()
mentionThread = threading.Thread(target = mentionStream)
mentionThread.start()

print("Successfully started information streams.")