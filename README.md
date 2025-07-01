# Minimax Speech-02-HD GUI Tool

An easy-to-use GUI tool for calling Minimax's Speech-02-HD text-to-speech model.

A user-friendly GUI tool for accessing the Minimax Speech-02-HD Text-to-Speech API.

! [App Screenshot](https://github.com/user-attachments/assets/e87e794b-1a8a-4ee8-bb64-2e1d8954d9ee) 

## Features

- Intuitive GUI
- Adjustable voice, speed, volume, and pitch
- Emotion selection
- Multi-language UI support
- Real-time playback and save as MP3 files.
- Advanced settings like bitrate and sample rate

## Installation

1. Make sure you have Python 3 installed. 
2. Clone or download the repository.
3. Install the required dependencies:
    ```bash
    pip install requests customtkinter pygame replicate
    ``

## How to Use

1. Run the Python script: `python "Minimax Speech-02-HD v0.8.py" `. 
2. Fill in your Replicate API key in the "API Key" input box. 
3. Enter the text you want to convert in the text box.
4. Adjust the parameters on the left as needed.
5. Click the "Generate" button. 
6. After successful generation, you can click "Play" or "Save".

## Notes

- The program will create a `temp_audio` folder in the same directory as the script to store temporary audio files, which will be cleaned up automatically when you close the program.
