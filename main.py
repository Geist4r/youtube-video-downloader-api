from flask import Flask, request, jsonify
import yt_dlp
import re
import os

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

def download_video(url, resolution):
    try:
        video_id = url.split('v=')[1].split('&')[0]
        out_dir = f"./downloads/{video_id}"
        os.makedirs(out_dir, exist_ok=True)
        
        # Use progressive format (video+audio combined, no ffmpeg needed)
        ydl_opts = {
            'format': f'best[height<={resolution[:-1]}][ext=mp4]',
            'outtmpl': os.path.join(out_dir, '%(title)s.%(ext)s'),
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'mweb', 'android'],
                    'skip': ['translated_subs']
                }
            },
            'http_headers': {
                'User-Agent': 'com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-us,en;q=0.5',
            }
        }
        
        # Add cookies if file exists
        if os.path.exists('./cookies.txt'):
            ydl_opts['cookiefile'] = './cookies.txt'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        return True, None
    except Exception as e:
        return False, str(e)

def get_video_info(url):
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'mweb', 'android'],
                    'skip': ['translated_subs']
                }
            },
            'http_headers': {
                'User-Agent': 'com.google.ios.youtube/19.29.1 (iPhone16,2; U; CPU iOS 17_5_1 like Mac OS X;)',
            }
        }
        
        # Add cookies if file exists
        if os.path.exists('./cookies.txt'):
            ydl_opts['cookiefile'] = './cookies.txt'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            video_info = {
                "title": info.get('title'),
                "author": info.get('uploader'),
                "length": info.get('duration'),
                "views": info.get('view_count'),
                "description": info.get('description'),
                "publish_date": info.get('upload_date'),
            }
            return video_info, None
    except Exception as e:
        return None, str(e)

def is_valid_youtube_url(url):
    pattern = r"^(https?://)?(www\.)?youtube\.com/watch\?v=[\w-]+(&\S*)?$"
    return re.match(pattern, url) is not None

@app.route('/download/<resolution>', methods=['POST'])
def download_by_resolution(resolution):
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "Missing 'url' parameter in the request body."}), 400

    if not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL."}), 400
    
    success, error_message = download_video(url, resolution)
    
    if success:
        return jsonify({"message": f"Video with resolution {resolution} downloaded successfully."}), 200
    else:
        return jsonify({"error": error_message}), 500

@app.route('/video_info', methods=['POST'])
def video_info():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "Missing 'url' parameter in the request body."}), 400

    if not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL."}), 400
    
    video_info, error_message = get_video_info(url)
    
    if video_info:
        return jsonify(video_info), 200
    else:
        return jsonify({"error": error_message}), 500


@app.route('/available_resolutions', methods=['POST'])
def available_resolutions():
    data = request.get_json()
    url = data.get('url')
    
    if not url:
        return jsonify({"error": "Missing 'url' parameter in the request body."}), 400

    if not is_valid_youtube_url(url):
        return jsonify({"error": "Invalid YouTube URL."}), 400
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {'youtube': {'player_client': ['ios']}},
        }
        
        # Add cookies if file exists
        if os.path.exists('./cookies.txt'):
            ydl_opts['cookiefile'] = './cookies.txt'
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            formats = info.get('formats', [])
            
            # Progressive (video+audio)
            progressive_resolutions = list(set([
                f"{f.get('height')}p"
                for f in formats
                if f.get('height') and f.get('vcodec') != 'none' and f.get('acodec') != 'none'
            ]))
            
            # All video formats
            all_resolutions = list(set([
                f"{f.get('height')}p"
                for f in formats
                if f.get('height') and f.get('vcodec') != 'none'
            ]))
            
            return jsonify({
                "progressive": sorted(progressive_resolutions, key=lambda x: int(x[:-1])),
                "all": sorted(all_resolutions, key=lambda x: int(x[:-1]))
            }), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
if __name__ == '__main__':
    from waitress import serve
    print("Starting YouTube Downloader API on port 5000...")
    serve(app, host='0.0.0.0', port=5000)
