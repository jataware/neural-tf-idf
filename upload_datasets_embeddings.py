from data.indicators import Indicators
from search.bert_search import BertSentenceSearch  # BertWordSearch
import json
from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")

print(es.info())

corpus = Indicators.get_corpus()

engine = BertSentenceSearch(corpus, cuda=False)  # using CPU
embeddings = engine.embeddings

featureCounter = 0

"""
Opening the raw jsonl file instead of matching corpus for now,
since we anyways need to insert the corpus as json (from its raw form).
The data has matched so far- same input, in same order, to generate embeddings
as to upload features to elasticsearch. We can revisit soon, especially if this
changes in the future.
"""
with open('data/indicators.jsonl') as f:
    lines = f.readlines()
    indicators = [json.loads(line)["_source"] for line in lines]
    f.close()

for doc in indicators:

    for feature in doc["outputs"]:

        embedding = embeddings[featureCounter]

        asList = embedding.tolist()
        print(f"Length of embedding to add: {len(asList)}")

        feature["embeddings"] = asList
        featureCounter += 1

        es.index(index="features", body=feature)

exit(0)
