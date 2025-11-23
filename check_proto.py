import google.generativeai as genai
try:
    print(dir(genai.protos.Tool))
except:
    print("Could not dir genai.protos.Tool")
