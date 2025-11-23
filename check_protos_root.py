import google.generativeai as genai
try:
    print(dir(genai.protos))
except:
    print("Could not dir genai.protos")
