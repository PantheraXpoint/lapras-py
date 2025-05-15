package kr.ac.kaist.cdsn.lapras.agents.datacollector;

import com.mongodb.MongoClient;
import com.mongodb.MongoCredential;
import com.mongodb.ServerAddress;
import com.mongodb.client.MongoCollection;
import com.mongodb.client.MongoDatabase;
import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.AgentConfig;
import kr.ac.kaist.cdsn.lapras.action.ActionInstance;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.communicator.LaprasTopic;
import kr.ac.kaist.cdsn.lapras.communicator.MessageType;
import kr.ac.kaist.cdsn.lapras.communicator.MqttCommunicator;
import kr.ac.kaist.cdsn.lapras.communicator.MqttTopic;
import kr.ac.kaist.cdsn.lapras.context.ContextInstance;
import kr.ac.kaist.cdsn.lapras.event.Event;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.event.EventType;
import kr.ac.kaist.cdsn.lapras.task.TaskInitiation;
import kr.ac.kaist.cdsn.lapras.task.TaskTermination;
import kr.ac.kaist.cdsn.lapras.user.UserNotification;
import org.apache.log4j.LogManager;
import org.bson.Document;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;

/**
 * Created by Daekeun Lee on 2016-11-15.
 * Last Modified: 2019-05-13
 */
public class DataCollectorAgent extends AgentComponent {
    private static final Logger LOGGER = LoggerFactory.getLogger(DataCollectorAgent.class);

    private final MqttCommunicator mqttCommunicator;
    private final AgentConfig agentConfig;
    private MongoClient mongoClient;
    private MongoCollection<Document> collection;
    private MongoDatabase database;

    public DataCollectorAgent(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        mqttCommunicator = agent.getMqttCommunicator();
        agentConfig = agent.getAgentConfig();
    }

    @Override
    public void run() {
        while(true);
    }

    @Override
    public void subscribeEvents() {
        subscribeEvent(EventType.MESSAGE_ARRIVED);
    }

    @Override
    public void setUp() {
        super.setUp();

        mqttCommunicator.subscribeTopic(new LaprasTopic(null, MessageType.CONTEXT, MqttTopic.MULTILEVEL_WILDCARD));

        String mongodbUsername = agentConfig.getOption("mongodb_username");
        String mongodbPassword = agentConfig.getOption("mongodb_password");
        String mongodbDBName = agentConfig.getOption("mongodb_dbname");
        MongoCredential credential = null;
        if(mongodbUsername != null && mongodbPassword != null) {
            credential = MongoCredential.createCredential(mongodbUsername, mongodbDBName, mongodbPassword.toCharArray());
        }

        ServerAddress serverAddress = new ServerAddress(agentConfig.getOption("mongodb_address"),
                Integer.parseInt(agentConfig.getOption("mongodb_port")));
        if(credential != null) {
            this.mongoClient = new MongoClient(serverAddress, Arrays.asList(credential));
        } else {
            this.mongoClient = new MongoClient(serverAddress);
        }
        database = this.mongoClient.getDatabase(mongodbDBName);
        collection = database.getCollection(agentConfig.getOption("mongodb_collection"));

        LogManager.getLogger("org.mongodb.driver.cluster").setLevel(org.apache.log4j.Level.OFF);
    }

    @Override
    public boolean handleEvent(Event event) {
        boolean result = super.handleEvent(event);
        MongoCollection<Document> userCollection = database.getCollection(agentConfig.getPlaceName() + "_user");
        MongoCollection<Document> taskCollection = database.getCollection(agentConfig.getPlaceName() + "_task");

        if(event.getType() == EventType.MESSAGE_ARRIVED) {
            LaprasTopic topic = (LaprasTopic) ((Object[]) event.getData())[0];
            byte[] payload = (byte[]) ((Object[]) event.getData())[1];

            Document document = new Document();
            switch(topic.getMessageType()) {
                case CONTEXT:
                    ContextInstance contextInstance = ContextInstance.fromPayload(payload);
                    if(contextInstance == null) {
                        LOGGER.info("The publisher does not speak the same protocol");
                        break;
                    }
                    if(contextInstance.getName().endsWith(AgentComponent.OPERATING_STATUS_SUFFIX)) {
                        break;
                    }
                    document.put("type", "context");
                    document.put("name", contextInstance.getName());
                    document.put("value", contextInstance.getValue());
                    document.put("timestamp", contextInstance.getTimestamp());
                    document.put("publisher", contextInstance.getPublisher());
                    collection.insertOne(document);
                    LOGGER.info("Inserted a context document of {}", contextInstance.getName());
                    break;
                case FUNCTIONALITY:
                    // TODO: Document insertion for functionalities and actions
                    break;
                case ACTION:
                    ActionInstance actionInstance = ActionInstance.fromPayload(payload);
                    if(actionInstance == null) {
                        LOGGER.info("The publisher does not speak the same protocol");
                        break;
                    }
                    document.put("type", "action");
                    document.put("name", actionInstance.getName());
                    document.put("timestamp", actionInstance.getTimestamp());
                    document.put("publisher", actionInstance.getPublisher());
                    collection.insertOne(document);
                    LOGGER.info("Inserted a action document of {}", actionInstance.getName());
                    break;
                case USER:
                    UserNotification userNotification = UserNotification.fromPayload(payload);
                    if (userNotification == null) {
                        LOGGER.info("The publisher does not speak the same protocol");
                        break;
                    }

                    document.put("type", "user");
                    document.put("name", userNotification.getName());
                    document.put("value", userNotification.getPresence());
                    document.put("timestamp", userNotification.getTimestamp());
                    document.put("publisher", userNotification.getPublisher());

                    userCollection.insertOne(document);
                    LOGGER.info("Inserted a user document of {}", userNotification.getName());
                    break;
                case TASK_INITIATION:
                    TaskInitiation taskInitiation = TaskInitiation.fromPayload(payload);
                    if (taskInitiation == null) {
                        LOGGER.info("The publisher does not speak the same protocol");
                        break;
                    }

                    document.put("type", "task_initiation");
                    document.put("task_id", taskInitiation.getId());
                    document.put("name", taskInitiation.getName());
                    document.put("users", taskInitiation.getInvolvedUsers());
                    document.put("timestamp", taskInitiation.getTimestamp());
                    document.put("publisher", taskInitiation.getPublisher());

                    taskCollection.insertOne(document);
                    LOGGER.info("Inserted a task document of {}", taskInitiation.getName());
                    break;
                case TASK_TERMINATION:
                    TaskTermination taskTermination = TaskTermination.fromPayload(payload);
                    if (taskTermination == null) {
                        LOGGER.info("The publisher does not speak the same protocol");
                        break;
                    }

                    document.put("type", "task_termination");
                    document.put("task_id", taskTermination.getTaskId());
                    document.put("timestamp", taskTermination.getTimestamp());
                    document.put("publisher", taskTermination.getPublisher());

                    taskCollection.insertOne(document);
                    LOGGER.info("Inserted a task document of {}", taskTermination.getName());
                    break;
            }
            return true;
        }
        return result;
    }
}
