import google.generativeai as genai
import pprint

print("genai attributes:")
print(dir(genai))

print("\ngenai.types attributes:")
try:
    print(dir(genai.types))
except:
    print("Could not dir genai.types")

