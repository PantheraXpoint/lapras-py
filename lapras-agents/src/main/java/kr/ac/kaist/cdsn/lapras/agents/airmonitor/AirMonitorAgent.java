package kr.ac.kaist.cdsn.lapras.agents.airmonitor;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.context.ContextField;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Created by Jeongwook on 2017-05-01.
 *
 * Periodically measure the air quality context & publish the context message.
 * Use Foobot(https://foobot.io) for measuring the air quality.
 *
 * Required configuration entries
 *     api_key: Foobot API Key
 *     api_baseurl: Foobot API base URL
 *     uuid: The UUID of Foobot that measures an air quality
 *
 * Publishing contexts
 *     ParticulateMatter (Double): The concentration of particulate matter (µg/m³)
 *     CarbonDioxide (Double): The concentration of carbon dioxide (ppm)
 *     VolatileCompounds (Double): The concentration of volatile compounds (ppb)
 *     AirPollution (Double): An air pollution rate (%)
 */

public class AirMonitorAgent extends AgentComponent {
    private static final Logger LOGGER = LoggerFactory.getLogger(AirMonitorAgent.class);

    private static final long PUBLISHING_TIME_INTERVAL = 10 * 60 * 1000;

    private static AirDataProvider provider = null;

    @ContextField(publishAsUpdated = true)
    public Context particulateMatter;

    @ContextField(publishAsUpdated = true)
    public Context carbonDioxide;

    @ContextField(publishAsUpdated = true)
    public Context volatileCompounds;

    @ContextField(publishAsUpdated = true)
    public Context airPollution;


    public AirMonitorAgent(EventDispatcher eventDispatcher, Agent agent) {

        super(eventDispatcher, agent);
        String apiKey = agent.getAgentConfig().getOption("api_key");
        String baseUri = agent.getAgentConfig().getOption("api_baseuri");
        String uuid = agent.getAgentConfig().getOption("uuid");

        provider = new FoobotAirDataProvider(apiKey, baseUri, uuid);
    }

    @Override
    public void run() {

        while (true) {
            try {
                AirData d = provider.get();
                final double pm = d.getParticulateMatter();
                final double co2 = d.getCarbonDioxide();
                final double voc = d.getVolatileCompounds();
                final double allpollu = d.getAirPollution();
                LOGGER.debug("pm: {}, co2: {}, voc: {}, allpollu: {}",
                        pm, co2, voc, allpollu);

                particulateMatter.updateValue(pm);
                carbonDioxide.updateValue(co2);
                volatileCompounds.updateValue(voc);
                airPollution.updateValue(allpollu);
            } catch (DataNotAvailableException e) {
                LOGGER.error("failed to get air quality data", e);
            }

            try {
                Thread.sleep(AirMonitorAgent.PUBLISHING_TIME_INTERVAL);
            } catch (InterruptedException e) {
                break;
            }
        }
    }
}