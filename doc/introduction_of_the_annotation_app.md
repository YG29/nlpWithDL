## Introduction of the Annotation App

The app consists of several dropdown menus and fields to fill in. On the left side there are two drop down menus that are responsible for navigating to the correct domain and scenario. 

Once selected desired domain and scenario, the conversation index will be shown in the "select match index" box which also serves as conversation navigator. There are two conversations per scenario. 

The system instruction will be shown. There are two ways of adding a system rule for generating the system rules. One way is to choose the rule from the dropdown menu where each sentence/paragraph is separated. Another way is to copy and paste part of the system instruction into the box and generate custom rules. 

The added system instruction rules are indexed and showed. After that, the conversation can be previewed. A dropdown menu can be used to select specific bot turn the annotator wich to add a distractor to. Once a specific bot turn of the dialog is selected, a distractor can be manually added to the distractor box. Below the box, a dropdown menu shows the rules previously added that can be chosen to attach to the distractor. 

After everything is added, an annotation is created at the bottom. After created desirable amount of annotations, the user may save them by clicking the button on the bottom left. A json file for this conversation will be created in the [annotation_saves] file. 

Something to improve later, currently, when switching to new scenarios, the rules and annotations need to be cleared/removed manually. 