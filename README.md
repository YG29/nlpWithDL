# Topic Following

```
project/
|
|----annotation_saves/ # -b annotate: saved annotation entries
|
|----csv_exports/ # -b post_annotate_process: process json annotations to csv entries
|
|----distractor_span/ # quality check for group 10
|
|----doc/
| └----meeting_notes/ # meeting notes on different dates
| └----annotation_split_decision.md # work split decision
| └----example_annotations.pdf # presentation example annotations
| └----Final_reflection_annotations.md # reflection at the end of the project
| └----initial_annotation_strategy.md
| └----initial_requirements_breakdown.md
| └----introduction_of_the_annotation_app.md # introduction to the app in -b annotate 
| └----NLP_Annotation_Guideline.pdf # annotation guideline after meeting with the other groups
|
|----final_annotations/ # csv files for final annotations
| └----combined_annotations.csv # all of group 6 annotations
| └----combined_annotations_guidelines.csv # mergeable formats with the other groups
| └----sampled_annotations.csv
| └----sampled_distractors_with_target.csv
| └----sampled_distractors_without_targets.csv # 20 sample distractors send to group 7 for quality control
|
|----Group10_sample/ # distractors received from group 10 for quality check
|
|----notebooks/ # fascilitating codes
|
|----src/
| └----annotate.py # -b annotate: streamlit annotation UI
| └----app_quality_control.py # -b post_annotate_process: streamlit quality control UI
| └----combine_csv.py # post process code
| └----combine_csv_guidelines.py # post process code for merging based on guideline
| └----post_annotate.py # post process code
|
└----README.md
|
└----requirements.txt # install the requirements before running any code
```

## Distractor Annotation

### General Workflow
The basic idea is to curate a human annotated dataset. In this dataset, high quality "off-topic" distractors are generated and inserted into a chatbot conversation regarding a specific domain and scenario. For each scenario, a system instruction is provided to guide the behavior of the LLM. Human annotators would generate topic rules based on these system instructions. Then, the human annotators go through the conversation and identify places where after the bot response, a distractor would be appropriate. Based on the identified topic rules, the human annotators write a distractor for that bot response and tag which rule the bot should follow for identifying it as a distractor. 

Overall, the human annotated data would have the following rough structure:

{domain/scenario/rules: ......}

{bot reponse: ......} {distractor: ......} {rule index: .....}


### Documentations of the Project

All documentations, meeting notes, methodologies, and design choices can be found in the [doc] folder including our presentations, annotation guidelines, and reflections. 


### The Annotation App

1. The annotation app can be found on the "annotate" branch. 
2. It reads the nvidia/CantTalkAboutThis-Topic-Control-Dataset, and fasciliates the human annotation of distractors process.
3. To run this app, first make sure to have installed the necessary packages:
                      ```pip install streamlit datasets```
4. A web version of the app will show up in the default browser with the following command: 
                      ```streamlit run src/annotate.py```
5. A detailed introduction of the app can be found: [doc/introduction_of_the_annotation_app.md]


### The Span App (quality control app)

1. The span app can be found on the "post_annotation_process" branch.
2. It reads the csv with group 10's 20 sample annotatation examples and you can use the app to save the span which you think breaks the system prompt in that case.
3. 3. To run this app, first make sure to have installed the necessary packages:
                      ```pip install streamlit datasets```
4. A web version of the app will show up in the default browser with the following command: 
                      ```streamlit run app_quality_control.py```


