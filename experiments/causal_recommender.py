from transformers import pipeline, set_seed
import re
import torch



class CausalRecommender:
    def __init__(self, model_name='gpt2-xl', device=None):
        if device is None:
            device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        self.generator = pipeline('text-generation', model=model_name, device=device)
        set_seed(42)
        self.template = lambda topic, is_cause: f"""General knowledge test. Please answer the following questions with single words or short phrases:

what are 3 causes of famine in America?
1. income inequality
2. lack of affordable housing
3. systemic racism

what are 3 effects of solar flares?
1. power outages
2. radio interference
3. auroras

what are 3 {'causes' if is_cause else 'effects'} of {topic}?
1."""

    @staticmethod
    def extract_causes(prompt:str, output:str) -> list[str]:
        output = output[len(prompt)-2:] #remove the prompt from the output, but keep the first number and dot ("1.")
        lines = output.split('\n')

        #remove any extra whitespace on lines, and remove any empty lines
        lines = [line.strip() for line in lines]
        lines = [line for line in lines if line]

        causes = []
        for line in lines:
            if not re.search(r'\d\.', line):
                break #when the pattern breaks, stop adding causes. The model may have asked a new question to continue the pattern
            
            #extract the cause without the number and dot
            line = re.sub(r'\d\.', '', line)
            line = line.strip()
            if line: #only if the line is not empty
                causes.append(line)

        return causes


    def get_results(self, topic:str, is_cause:bool) -> list[str]:
        prompt = self.template(topic, is_cause)
        outputs = self.generator(prompt, max_length=100, num_return_sequences=3, pad_token_id=50256)
        causes = set()
        for output in outputs:
            causes_i = CausalRecommender.extract_causes(prompt, output['generated_text'])
            causes.update(causes_i)

        return list(causes)

    def get_causes(self, topic:str) -> list[str]:
        return self.get_results(topic, True)

    def get_effects(self, topic:str) -> list[str]:
        return self.get_results(topic, False)



def main():
    recommender = CausalRecommender(device='cpu')

    print('Enter a topic to generate causes or effects for.\ne.g. "causes of climate change" or "effects of inflation".\nIf none is specified, "causes" is assumed.')
    while True:
        topic = input('>>> ')
        if topic.startswith('causes of'):
            is_cause = True
            topic = topic[9:].strip()
        elif topic.startswith('effects of'):
            is_cause = False
            topic = topic[10:].strip()
        else:
            #move the terminal back one line
            print('\033[F', end='')
            print(f'>>> causes of {topic}')
            is_cause = True
            topic = topic.strip()

        results = recommender.get_results(topic, is_cause)
        for result in results:
            print(f'- {result}')


if __name__ == '__main__':
    main()