from __future__ import annotations
from transformers import BertTokenizerFast, BertModel, BatchEncoding, logging # type: ignore[import]
import torch
from typing import TypedDict


class Highlight(TypedDict):
    text: str
    highlight: bool


class Highlighter:
    
    ignore_words = {
        # language model special tokens
        '[CLS]', '[SEP]',
        # stopwords
        'i', 'me', 'my', 'myself', 'we', 'our', 'ours', 'ourselves', 'you', 'your', 'yours', 'yourself', 'yourselves', 'he', 'him', 'his', 'himself', 'she', 'her', 'hers', 'herself', 'it', 'its', 'itself', 'they', 'them', 'their', 'theirs', 'themselves', 'what', 'which', 'who', 'whom', 'this', 'that', 'these', 'those', 'am', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'having', 'do', 'does', 'did', 'doing', 'a', 'an', 'the', 'and', 'but', 'if', 'or', 'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 'with', 'about', 'against', 'between', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'to', 'from', 'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 'again', 'further', 'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very', 's', 't', 'can', 'will', 'just', 'don', 'should', 'now', 
    }

    def __init__(self, model='bert-base-uncased'):
        # load BERT tokenizer and model from HuggingFace
        with torch.no_grad():
            logging.set_verbosity_error()
            self.tokenizer = BertTokenizerFast.from_pretrained(model)
            self.model = BertModel.from_pretrained(model)

            # move model to GPU
            if torch.cuda.is_available():
                self.model = self.model.cuda()

        # save the device
        self.device = next(self.model.parameters()).device
    
    @staticmethod
    def good_match(word):
        """check if a word is a stopword, or only contains punctuation. Such words should not be highlighted."""
        return word not in Highlighter.ignore_words and len(re.sub('[^a-zA-Z]', '', word)) > 0

        
    def embed(self, s: str) -> tuple[BatchEncoding ,torch.Tensor]:
        with torch.no_grad():
            tokens = self.tokenizer(s, return_tensors='pt', padding=True, truncation=True)
            tokens.to(device=self.device)
            embedding = self.model(**tokens).last_hidden_state[0]
            
            return tokens, embedding
        
    def highlight(self, query: str, target: str, threshold=0.5, embedding_q=torch.Tensor|None) -> list[Highlight]:
        """Highlight a single target string given a query"""

        # embed the query if it is not already embedded
        if embedding_q is None:
            _, embedding_q = self.embed(query)

        # embed the target string and grab the tokenization
        token_t_obj, embedding_t = self.embed(target)
        token_t = token_t_obj.tokens()

        # find the match score for every token in the target string compared to the query
        matchings = torch.stack([torch.nn.functional.cosine_similarity(q, embedding_t) for q in embedding_q])

        # determine which tokens in the target are above the match threshold
        matched_tokens = (matchings > threshold).any(dim=0)
        matched_indices = [(i,token) for i,(token,match) in enumerate(zip(token_t,matched_tokens)) if match and self.good_match(token)]

        # determine the spans that will be highlighted: 
        # 1. combine together tokens that make up larger words via the "##" prefix (which may be missing from the matched_indices list)
        highlight_token_indices = []
        for i, _ in matched_indices:
            start = i
            end = start
            if token_t[start].startswith('##'):
                while token_t[start-1].startswith('##'):
                    start -= 1
                start -= 1
            while end + 1 < len(token_t) and token_t[end + 1].startswith('##'):
                end += 1
            highlight_token_indices.append((start, end))

        # 2. merge adjacent and overlapping spans into a single span
        highlight_token_indices.sort()
        merged_spans = []
        for span in highlight_token_indices:
            if len(merged_spans) == 0:
                merged_spans.append(span)
            else:
                if span[0] <= merged_spans[-1][1] + 1:
                    merged_spans[-1] = (merged_spans[-1][0], max(merged_spans[-1][1], span[1]))
                else:
                    merged_spans.append(span)

        # 3. convert the token indices to character indices in the original text
        highlight_char_spans = []
        for start, end in merged_spans:
            start_char = token_t_obj.token_to_chars(start).start
            end_char = token_t_obj.token_to_chars(end).end
            highlight_char_spans.append((start_char, end_char))

        # 4. convert the spans and original text to a list of Highlight objects
        highlight: list[Highlight] = []
        last_end = 0
        for start, end in highlight_char_spans:
            if start > last_end:
                highlight.append({
                    "text": target[last_end:start],
                    "highlight": False
                })
            highlight.append({
                "text": target[start:end], 
                "highlight": True
            })
            last_end = end
        
        if last_end < len(target):
            highlight.append({
                "text": target[last_end:], 
                "highlight": False
            })

        return highlight
        
    def highlights(self, query: str, targets: list[str], threshold=0.5) -> list[list[Highlight]]:
        """highlight multiple target strings given a query"""    
        _, embedding_q = self.embed(query)
        highlights = [self.highlight(query, target, threshold, embedding_q) for target in targets]
        return highlights
            


#terminal color/background ANSI codes
ansi_color_codes = {
    'black': 30,
    'red': 31,
    'green': 32,
    'yellow': 33,
    'blue': 34,
    'magenta': 35,
    'cyan': 36,
    'white': 37,
    'bright_black': 90,
    'bright_red': 91,
    'bright_green': 92,
    'bright_yellow': 93,
    'bright_blue': 94,
    'bright_magenta': 95,
    'bright_cyan': 96,
    'bright_white': 97,
}
ansi_background_codes = {
    'black': 40,
    'red': 41,
    'green': 42,
    'yellow': 43,
    'blue': 44,
    'magenta': 45,
    'cyan': 46,
    'white': 47,
    'bright_black': 100,
    'bright_red': 101,
    'bright_green': 102,
    'bright_yellow': 103,
    'bright_blue': 104,
    'bright_magenta': 105,
    'bright_cyan': 106,
    'bright_white': 107,
}

def terminal_highlight_print(highlight:list[Highlight], background='bright_white', color='black'):
    """print the text to the terminal, highlighting at the given spans"""

    color = ansi_color_codes[color]
    background = ansi_background_codes[background]

    # print the chunks
    for span in highlight:
        chunk = span['text']
        highlight = span['highlight']
        if highlight:
            print(f'\033[{color};{background}m{chunk}\033[0m', end='')
        else:
            print(chunk, end='')

    print()


 



def main():
    from data.dart_papers import DartPapers
    from easyrepl import REPL
    from search.bert_search import BertSentenceSearch
    import re

    #blacklist function, reject results with less than some number of alphabetical characters
    pattern = re.compile('[^a-zA-Z]')
    N = 500
    blacklist_fn = lambda x: len(x) < N or len(pattern.sub('', x)) < N

    corpus = DartPapers.get_paragraph_corpus()
    engine = BertSentenceSearch(corpus, save_name=DartPapers.__name__, blacklist=blacklist_fn)
    highlighter = Highlighter()

    for query in REPL():
        matches = engine.search(query, n=5)
        raw_texts = [corpus[match_id] for match_id, score in matches]
        highlights = highlighter.highlights(query, raw_texts)
        for highlight in highlights:
            terminal_highlight_print(highlight)
            print()
                
        
        

if __name__ == '__main__':
    main()