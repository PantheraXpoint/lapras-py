package kr.ac.kaist.cdsn.lapras.agents.airmonitor;

import com.mashape.unirest.http.*;
import com.mashape.unirest.http.exceptions.UnirestException;
import com.mashape.unirest.request.GetRequest;
import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

/**
 * Created by Jeongwook on 2017-05-01.
 *
 * Provide air quality data using Foobot API
 */

public class FoobotAirDataProvider implements AirDataProvider {
    // Index of particulate matter in the given data
    public static final int INDEX_PARTICULATE_MATTER = 1;
    // Index of carbon dioxide in the given data
    public static final int INDEX_CARBON_DIOXIDE = 4;
    // Index of volatile compounds in the given data
    public static final int INDEX_VOLATILE_COMPOUNDS = 5;
    // Index of air pollution rate in the given data
    public static final int INDEX_AIR_POLLUTION = 6;

    private final GetRequest req;

    /**
     * @param apiKey Foobot API key.
     * @param baseUri Foobot API URL.
     * @param uuid The UUID of the foobot that measure air quality.
     */
    FoobotAirDataProvider(String apiKey, String baseUri, String uuid) {
        // Formulate GET request.
        this.req = Unirest.get(baseUri)
                .header("Accept", "application/json;charset=UTF-8")
                .header("X-API-KEY-TOKEN", apiKey)
                .routeParam("uuid", uuid)
                // Get the air quality data measured during last 5 minutes.
                // Foobot publishes the air quality data every 5 minutes.
                .routeParam("period", "300")
                // Does not collect the avaerage of the air quality data.
                .routeParam("averageBy", "0");
    }

    @Override
    public AirData get() throws DataNotAvailableException {
        try {
            HttpResponse<JsonNode> res = req.asJson();
            JsonNode node = res.getBody();
            if (node.isArray()) {
                throw new DataNotAvailableException("response should not be an array");
            }

            JSONArray datapoint = node.getObject().getJSONArray("datapoints").getJSONArray(0);
            double pm = datapoint.getDouble(INDEX_PARTICULATE_MATTER);
            double co2 = datapoint.getDouble(INDEX_CARBON_DIOXIDE);
            double voc = datapoint.getDouble(INDEX_VOLATILE_COMPOUNDS);
            double allpollu = datapoint.getDouble(INDEX_AIR_POLLUTION);

            return new AirData(pm, co2, voc, allpollu);
        } catch (UnirestException e) {
            throw new DataNotAvailableException(e);
        } catch (JSONException e) {
            throw new DataNotAvailableException("invalid datapoint", e);
        } catch (IllegalArgumentException e) {
            throw new DataNotAvailableException("invalid datapoint", e);
        }
    }

    @Override
    public void close() throws Exception {
        Unirest.shutdown();
    }
}