
# Creating and populating a new Features index from Indicators index

### Create `features` index

```
PUT /features
{
  "mappings": {
    "properties": {
      "embeddings": {
        "type": "dense_vector",
        "dims": 768
      }
    }
  }
}
```

### Loop through indicators and upload Features

This will upload features alongside embeddings:

`python process_all_indicators_embedd_features.py`
