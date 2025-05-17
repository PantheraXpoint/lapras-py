package kr.ac.kaist.cdsn.lapras.rest;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.Component;
import kr.ac.kaist.cdsn.lapras.event.Event;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import org.glassfish.grizzly.http.server.HttpServer;
import org.glassfish.jersey.grizzly2.httpserver.GrizzlyHttpServerFactory;
import org.glassfish.jersey.server.ResourceConfig;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.IOException;
import java.net.URI;
import java.net.URISyntaxException;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;

/**
 * Created by Daekeun Lee on 2016-11-29.
 */
public class RestServer extends Component {
    private static final Logger LOGGER = LoggerFactory.getLogger(RestServer.class);

    private final int port;
    private static ConcurrentMap<Integer, RestServer> instanceMap = new ConcurrentHashMap<>();

    private HttpServer server;

    public static RestServer getInstance(Integer port) {
        return instanceMap.get(port);
    }

    public RestServer(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        port = Integer.parseInt(agent.getAgentConfig().getOptionOrDefault("rest_port", "8080"));
        instanceMap.put(port, this);
    }

    @Override
    protected void subscribeEvents() {

    }

    @Override
    public void setUp() {
        URI uri;
        ResourceConfig resourceConfig = new ResourceConfig()
                .register(RootResource.class)
                .register(ContextResource.class)
                .register(FunctionalityResource.class)
                .register(RuleResource.class)
                .register(QLearningResource.class)
                .register(UserResource.class)
                .register(TaskResource.class);
        try {
            uri = new URI("http://0.0.0.0:" + String.valueOf(port));
            server = GrizzlyHttpServerFactory.createHttpServer(uri, resourceConfig);
            server.start();
            LOGGER.info("Rest server launched on {}", uri);
        } catch (IOException e) {
            LOGGER.error("An error occurred while starting rest server", e);
            return;
        } catch (URISyntaxException e) {
            LOGGER.error("Failed to parse URI", e);
            return;
        }
    }

    public Agent getAgent() {
        return agent;
    }

    @Override
    protected boolean handleEvent(Event event) {
        return false;
    }
}
