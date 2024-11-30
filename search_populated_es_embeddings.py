from data.indicators import Indicators
from search.bert_search import BertSentenceSearch
from elasticsearch import Elasticsearch
import json

es = Elasticsearch("http://localhost:9200")

print(es.info())

# load a corpus of documents, and set up a search engine
corpus = Indicators.get_corpus()
engine = BertSentenceSearch(corpus, cuda=False)

# hardcoded query to search through es feature documents
query = 'number of people who have been vaccinated'
print('Query:', query)

# Embedding for input query
embedding = engine.embed_query(query)

# If searchin datasets, with nested features within it (properties are really named datasets.outputs)
datasets_query = {
  "_source": [
    "id",
    "name"
  ],
  "size": 10,
  "query": {
    "nested": {
      "inner_hits": {},
      "path": "outputs",
      "query": {
        "script_score": {
          "query": {
            "match_all": {}
          },
          "script": {
            "source": "cosineSimilarity(params.query_vector, 'outputs.embeddings') + 1.0",
            "params": {
                "query_vector": embedding.tolist()
            }
          }
        }
      }
    }
  }
}

# If searchin features as a top-level index
features_query = {
    "query": {
        "script_score": {
            "query": {"match_all": {}},
            "script": {
                "source": "cosineSimilarity(params.query_vector, 'embeddings') + 1.0",
                "params": {
                    "query_vector": embedding.tolist()
                }
            }
        }
    },
    "_source": [
        "unit",
        "is_primary",
        "name",
        "description",
        "unit_description",
        "display_name",
        "type"
    ]
}

results = json.dumps(es.search(index="features", body=features_query)["hits"]["hits"])
# results = json.dumps(es.search(index="datasets", body=datasets_query)["hits"]["hits"])

print(f"Results:\n{results}")
