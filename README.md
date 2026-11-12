In this folder there are two projects for potential node integration:

1) yt_transcribe.py: This is a transcriber program that will take any youtube link, download the audio from it, and provide a transcription file in .txt format.

2) character_voice.py: This is a program that will make a custom voice from an input dialogue and a character description, and allows you to save these custom voices to your ElevenLabs account.

Output mp3s for the character voice program are saved in the outputs folder.

You must create a .env.local file in VS code that contains the ElevenLabs API key in the below format and keep that in the root folder for this to work:

ELEVENLABS_API_KEY="YOUR_API_KEY"