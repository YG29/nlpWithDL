## Initial Requirements Breakdown for Annotation

The goal is to generate distractors for the conversation manually to test if the LLM can identify such distractors. 

### How the LLM works?

1. There are different domains and for each domain there are different scenarios. 
2. For each scenario, there is a specific system instruction prompting the LLM to adhere to these guidelines and generate conversations
3. For the distractors, the LLM should gently decline the user and navigate the conversation back to allowed content. 

### Distractors

Requirements for the distractors:

1. Distractors should flow naturally in the conversation
2. Distractors should be off-topic with respect to the system instruction
3. Each distractor should break specific requirements from the system instructions
3. Adversarial distractors are also possible. Common jailbreaks or trick stories. 

