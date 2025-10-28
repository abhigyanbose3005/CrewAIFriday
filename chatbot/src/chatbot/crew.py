from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai.agents.agent_builder.base_agent import BaseAgent
from typing import List
from crewai_tools import RagTool
import yaml
# If you want to run a snippet of code before or after the crew starts,
# you can use the @before_kickoff and @after_kickoff decorators
# https://docs.crewai.com/concepts/crews#example-crew-class-with-decorators

@CrewBase
class Chatbot():
    """Chatbot crew"""

    agents_config_path = 'src/chatbot/config/agents.yaml'
    tasks_config_path = 'src/chatbot/config/tasks.yaml'

    def __init__(self):
        # Load YAML files once, convert to dicts
        with open(self.agents_config_path, 'r') as f:
            self.agents_config = yaml.safe_load(f)

        with open(self.tasks_config_path, 'r') as f:
            self.tasks_config = yaml.safe_load(f)

        self.agents=[]
        self.tasks=[]

    # Learn more about YAML configuration files here:
    # Agents: https://docs.crewai.com/concepts/agents#yaml-configuration-recommended
    # Tasks: https://docs.crewai.com/concepts/tasks#yaml-configuration-recommended
    
    # If you would like to add tools to your agents, you can learn more about it here:
    # https://docs.crewai.com/concepts/agents#agent-tools
    @agent
    def knowledge_agent(self) -> Agent:
        return Agent(
            config=self.agents_config['knowledge_agent'], # type: ignore[index]
            verbose=True
        )

    # To learn more about structured task outputs,
    # task dependencies, and task callbacks, check out the documentation:
    # https://docs.crewai.com/concepts/tasks#overview-of-a-task
    @task
    def knowledge_task(self) -> Task:
        return Task(
            config=self.tasks_config['knowledge_task'], # type: ignore[index]
        )

    @crew
    def crew(self) -> Crew:
        """Creates the Chatbot crew"""
        # To learn how to add knowledge sources to your crew, check out the documentation:
        # https://docs.crewai.com/concepts/knowledge#what-is-knowledge

        return Crew(
            agents=self.agents, # Automatically created by the @agent decorator
            tasks=self.tasks, # Automatically created by the @task decorator
            process=Process.hierarchical,
            verbose=True,
            # process=Process.hierarchical, # In case you wanna use that instead https://docs.crewai.com/how-to/Hierarchical/
        )
