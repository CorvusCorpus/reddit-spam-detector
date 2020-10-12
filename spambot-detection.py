import praw, requests, json, time

DEEPAI_API_KEY = ''

reddit = praw.Reddit("corvus", user_agent='Repost Bot Detector by Corvus')

# Check against older posts that have a karma score of at least this value                  
karma_threshold = 5000

# Only check a post if the OP has a link karma score below this value
user_score_threshold = 10000

# The maximum distance threshold between two images to be considered identical, as measured by DeepAI
similarity_threshold = 10

def compare_images(post1, post2):
    # Don't bother with posts that aren't still images
    if (post1.url[-3:] != "png" and post1.url[-3:] != "jpg") or (post2.url[-3:] != "png" and post2.url[-3:] != "jpg"):
        return False
    r = requests.post(
    "https://api.deepai.org/api/image-similarity",
    data={
        'image1': post1.url,
        'image2': post2.url,
    },
    headers={'api-key': DEEPAI_API_KEY})
    try:
        result = r.json()['output']['distance'] <= similarity_threshold
        return result
    except: 
        print("DeepAI API call error - please investigate")
        print(post1.url + ", " + post2.url)
        print(r.json())
        return False
           
def detect_repost(post):
    ps_results = requests.get('https://api.pushshift.io/reddit/search/submission/?size=10&sort=desc&score=>' + str(karma_threshold) + '&q="' + post.title + '"&subreddit=' + post.subreddit.display_name)
    for r in json.loads(ps_results.text)['data']:
        if r['author'] != post.author.name:
            og_post = reddit.submission(id=r['id'])
            if og_post.title.lower() == post.title.lower():
                # Check if exact link has been used before
                if og_post.url == post.url:
                    return (str(post.permalink) + "\n" + str(og_post.permalink))
                # Otherwise, perform image recognition check
                elif(compare_images(post, og_post)):
                    return (str(post.permalink) + "\n" + str(og_post.permalink))
    return None
    
def scan_sub(sub):
    for p in reddit.subreddit(sub).stream.submissions():
        if p.author.link_karma < user_score_threshold:
            result = detect_repost(p)
            if result is not None:
                print("Exact repost with same title detected:\n" + result)
         
while(True):
    try:
        scan_sub("aww+pics")
    except:
        print("Something borked, restart for now")
        time.sleep(60)

    
        

