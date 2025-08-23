# LogSentinel
---

In this project, I aimed to build an agentic workflow to evaluate application logs and send notiifcations in case of errors or events requiring action. This workflow consisted of 2 producers being seperate microservices in my PicRater project, sending logs to a kafka broker. These logs were then consumed by 4 seperate containerized LangGraph workflows. The LangGraph workflows would process the logs and store a timestamped summary and general evaluation of the logs into a PostgreSQL database, and sent notifications for any events that required attention.

</br></br>
### High Level Architecture
---
<img width="1277" height="390" alt="image" src="https://github.com/user-attachments/assets/a0bea623-0452-4ad8-81b3-6cdfe3f88030" />


</br>

This architecture runs on 2 seperate AWS EC2 instances. The instance running the Kafka cluster runs 2 containerized Kafka brokers. The Kafka cluster is configured with a replication factor of 2, enabling one to be the leader, and the other to be a replica. The second EC2 instance contains 2 Kafka consumer groups, with each group having 2 consumers. The consumers would poll for messages and run workflows that process the logs. 

</br></br>
### Kafka Architecture
---
<img width="1236" height="511" alt="image" src="https://github.com/user-attachments/assets/441d856e-d3aa-4d7f-b57c-3232eeeafa9e" />

</br>

The producers, which were seperate .NET applications running as services in a microservice architecture, send logs to seperate topics. Within each topic, the messages are partitioned into 2 partitions, where each consumer group reads from its respective partition. This architecture more more closely follows a queueing model than a PubSub model, as each producer sends a message once and a consumer processes it once.

</br></br>
### LangGraph Workflow
---

<div align="center">
  <img width="259" height="555" alt="image" src="https://github.com/user-attachments/assets/79ce0366-6879-4120-8def-0d4216f95000" />
</div>

The consumer polls the Kafka cluster for a period of 2 seconds and passes the batch of logs into the agentic workflow. The first agent performs a high level evaluation of the logs (either good or bad). If the logs are bad, an agent calls a notification tool that sends an email notification via AWS SNS. Lastly, a final agent generates a summary and saves it to the database.

</br></br>
### Conclusion
---
Overall, this project served to offer fundamental, hands-on experience with Kafka and agentic AI development by applying them to a industry relavent use case.
