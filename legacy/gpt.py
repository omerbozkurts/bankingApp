from openai import OpenAI

client= OpenAI(api_key= "api`_key")

def gptSohbet(prompt):
    cevap=client.chat.completions.create(
        model='gpt-3.5-turbo',
        messages=[{"role":"user","content":prompt}],
    )

    return cevap.choices[0].message.content.strip()

if __name__=="__main__":
    while True:
        user_input = input("Siz:")
        if user_input.lower in ['cik','cikis','cikis yap','bitir','sonlandir']:
            break

        cevap= gptSohbet(user_input)
        print("GPT'nin yaniti: ",cevap)