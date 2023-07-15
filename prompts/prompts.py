import os
import openai

openai.api_key = os.getenv("OPENAI_API_KEY")


def chat(prompt):
    completion = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": str(prompt)},
        ],
    )
    response = completion["choices"][0]["message"]["content"]
    return response


class OODA(object):
    def __init__(self, observation):
        self.observation = observation
        self.decision = None
        self.action = None

        self.decision_prompt = self.build_decision_prompt(observation)
        self.decision = chat(self.decision_prompt)

        self.action_prompt = self.build_action_prompt(self.decision)
        self.action = chat(self.action_prompt)

    def build_decision_prompt(self, observation):
        return f"""
### OBSERVATION ###
(This first section involves collecting information about the current
task, both internally and externally. By observing and analyzing the available
information, you gain awareness of the circumstances and identify potential
next steps.)

```
{observation}
```

### ORIENTATION ###
(Once you have reviewed the necessary information above, the next step is to orient
yourself by interpreting and analyzing the data. This stage involves
understanding the context, assessing the significance of the observations, and
evaluating how they relate to your existing knowledge and mental models. By
orientating yourself effectively, you develop a deeper understanding of the
situation, enabling you to make more informed decisions.)

My Situation: I am the Worker assigned to this Task which was created by my Client.
My Goal: Help the client complete this task so they mark it as complete.
My Options:
- I can ask an internet search engine to search the internet for information.
- I can ask a web browser to access a URL.
- I can ask a calculator to perform a calculation.
- I can ask the client for more information.
- I can provide a status update to the client in a message.
- I can summarize information for myself and the client in a message.
- I can respond directly in a message.

### DECISION ###
(In this section, you use the insights gained from observation and orientation
to make a decision to help achieve your goal. This involves considering
various courses of action, evaluating their potential outcomes, and selecting
the most suitable option based on your analysis. It is crucial to consider
both short-term and long-term implications and weigh the risks and benefits
associated with each decision. Write your final decision at the end in a
single sentence.)

"""

    def build_action_prompt(self, decision):
        return f"""

{self.decision_prompt}

{self.decision}

### ACT ###

All actions use the following syntax, similar to python functions:

ACTION_NAME(ARGUMENTS).

I have the following actions available to me:
- SEARCH_WEB(QUERY)
- ACCESS_URL(URL)
- CALCULATE_EXPRESSION(EXPRESSION)
- MESSAGE_CLIENT(MESSAGE)

Given the decision above, I will perform the following action:

"""


if __name__ == "__main__":
    while True:
        prompt = input("Enter your prompt: ")  # ex: "Client: Book a dinner for 2"
        ooda = OODA(prompt)
        print(f"OBS: {ooda.observation}")
        print(f"DECISION: {ooda.decision}")
        print(f"ACT: {ooda.action}")


# Client: I got a dent on my car and need to find a body shop nearby. can you help me find a good one
# Worker: Could you please provide me with your location so that I can find nearby body shops for you?
# Client: I am located in San Francisco, CA
