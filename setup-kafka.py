from kafka.admin import KafkaAdminClient, NewTopic

admin_client = KafkaAdminClient(
    bootstrap_servers="54.166.188.31:9092", 
    client_id='test'
)

user_topic = NewTopic(name="user-service-logs-topic", 
                      num_partitions=2, 
                      replication_factor=2)

pic_topic  = NewTopic(name="pic-service-logs-topic", 
                      num_partitions=2, 
                      replication_factor=2)

admin_client.create_topics(new_topics=[user_topic, pic_topic], validate_only=False)