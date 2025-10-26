# Topic Following

```
project/
|
|----annotation_saves/ # -b annotate: saved annotation entries
|
|----doc/
| └----additional_requirements_20oct.md # meeting notes form 20 Oct
| └----initial_annotation_strategy.md 
| └----initial_requirements_breakdown.md
| └----introduction_of_the_annotation_app.md # introduction to the app in -b annotate 
|
|----notebooks/
|
|----src/
| └----annotate.py # -b annotate: streamlit annotation UI
|
└----README.md
```

## Distractor Annotation

### General Workflow
The basic idea is to curate a human annotated dataset. In this dataset, high quality "off-topic" distractors are generated and inserted into a chatbot conversation regarding a specific domain and scenario. For each scenario, a system instruction is provided to guide the behavior of the LLM. Human annotators would generate topic rules based on these system instructions. Then, the human annotators go through the conversation and identify places where after the bot response, a distractor would be appropriate. Based on the identified topic rules, the human annotators write a distractor for that bot response and tag which rule the bot should follow for identifying it as a distractor. 

Overall, the human annotated data would have the following rough structure:

{domain/scenario/rules: ......}

{bot reponse: ......} {distractor: ......} {rule index: .....}


### The Annotation App

1. The annotation app can be found on the "annotate" branch. 
2. It reads the nvidia/CantTalkAboutThis-Topic-Control-Dataset, and fasciliates the human annotation of distractors process.
3. To run this app, first make sure to have installed the necessary packages:
                      ```pip install streamlit datasets```
4. A web version of the app will show up in the default browser with the following command: 
                      ```streamlit run src/annotate.py```
5. A detailed introduction of the app can be found: [doc/introduction_of_the_annotation_app.md]


