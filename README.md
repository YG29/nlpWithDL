# Topic Following

'
project/
|
|-

'

file structure: 

src -- helper programs

notebooks -- jupyter notebooks for exploratory purposes

doc -- concept development logs and documentations

annotation_saves -- saved json files for annotations of distractors

## Distractor Annotation

### General Workflow
The basic idea is to curate a human annotated dataset. In this dataset, high quality "off-topic" distractors are generated and inserted into a chatbot conversation regarding a specific domain and scenario. For each scenario, a system instruction is provided to guide the behavior of the LLM. Human annotators would generate topic rules based on these system instructions. Then, the human annotators go through the conversation and identify places where after the bot response, a distractor would be appropriate. Based on the identified topic rules, the human annotators write a distractor for that bot response and tag which rule the bot should follow for identifying it as a distractor. 

Overall, the human annotated data would have the following rough structure:

{domain/scenario/rules: ......}

{bot reponse: ......} {distractor: ......} {rule index: .....}


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

Once selected desired domain and scenario, the conversation index will be shown in the "select match index" box which also serves as conversation navigator. There are two conversations per scenario. 

The system instruction will be shown. There are two ways of adding a system rule for generating the system rules. One way is to choose the rule from the dropdown menu where each sentence/paragraph is separated. Another way is to copy and paste part of the system instruction into the box and generate custom rules. 

The added system instruction rules are indexed and showed. After that, the conversation can be previewed. A dropdown menu can be used to select specific bot turn the annotator wich to add a distractor to. Once a specific bot turn of the dialog is selected, a distractor can be manually added to the distractor box. Below the box, a dropdown menu shows the rules previously added that can be chosen to attach to the distractor. 

After everything is added, an annotation is created at the bottom. After created desirable amount of annotations, the user may save them by clicking the button on the bottom left. A json file for this conversation will be created in the [annotation_saves] file. 

Something to improve later, currently, when switching to new scenarios, the rules and annotations need to be cleared/removed manually. 