import praw, requests, json, time

DEEPAI_API_KEY = ''

reddit = praw.Reddit("corvus", user_agent='Repost Bot Detector by Corvus')

# Check against older posts that have a karma score of at least this value                  
karma_threshold = 2000

# Only check a post if the OP has a link karma score below this value
user_score_threshold = 10000

# The maximum distance threshold between two images to be considered identical, as measured by DeepAI
similarity_threshold = 10

# Comment template for reporting a positive hit
comment = "This submission is an exact-title, same image repost of the following high karma post:\n\nhttps://reddit.com%s\n\nPlease investigate this account, as it is likely they may be an account \
           farmer or reposting spam bot."

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
    # PushShift sometimes fails to update post scores for < year old submissions and defaults to 1, so check these also
    ps_results = requests.get('https://api.pushshift.io/reddit/search/submission/?size=10&sort=asc&score>=' + str(karma_threshold) + '&q="' + post.title + '"&subreddit=' + post.subreddit.display_name)
    ps_score_one = requests.get('https://api.pushshift.io/reddit/search/submission/?size=10&sort=desc&score=1&q="' + post.title + '"&subreddit=' + post.subreddit.display_name)
    
    for r in (json.loads(ps_results.text)['data'] + json.loads(ps_score_one.text)['data']):
        if r['author'] != post.author.name and r['title'].lower() == post.title.lower() and (r['score'] == 1 or r['score'] >= karma_threshold):
            og_post = reddit.submission(id=r['id'])
            if og_post.score >= karma_threshold:
                # Check if exact link has been used before
                if og_post.url == post.url:
                    return og_post
                # Otherwise, perform image recognition check
                elif(compare_images(post, og_post)):
                    return og_post
    return None
    
def scan_sub(sub):
    for p in reddit.subreddit(sub).stream.submissions():
        if p.author.link_karma < user_score_threshold:
            result = detect_repost(p)
            if result is not None:
                print("Exact repost with same title detected:\n" + p.permalink + "\n" + result.permalink + "\n")
                p.reply(comment % result.permalink)
         
while(True):
    try:
        scan_sub("aww+pica")
    except:
        print("Something borked, restart for now")
        time.sleep(60)


    
        

