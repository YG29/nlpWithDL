# Topic Following
# nlp with deep learning

## Distractor Annotation

### The Annotation App

1. The annotation app can be found on the "annotate" branch. 
2. It reads the nvidia/CantTalkAboutThis-Topic-Control-Dataset, and fasciliate the human annotation of distractors process.
3. To run this app, first make sure to have installed the necessary packages: 
                      pip install streamlit datasets
4. A web version of the app will show up in the default browser with the following command: 
                      streamlit run src/annotate.py
5. A detailed introduction of the app can be found in the section [Introduction of the Annotation App]


### Introduction of the Annotation App

The app consists of several dropdown menus and fields to fill in. On the left side there are two drop down menus that are responsible for navigating to the correct domain and scenario. 

Once selected desired domain and scenario, the conversation index will be shown in the "select match index" box which also serves as conversation navigator. There are two conversasions per scenario. 

The system instruction will be shown. There are two ways of adding a system rule for generating the system rules. 

