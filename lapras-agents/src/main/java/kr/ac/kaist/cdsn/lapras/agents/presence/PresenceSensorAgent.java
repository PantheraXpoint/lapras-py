package kr.ac.kaist.cdsn.lapras.agents.presence;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.agent.AgentComponent;
import kr.ac.kaist.cdsn.lapras.agent.Context;
import kr.ac.kaist.cdsn.lapras.context.ContextField;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.learning.data.ArffDataInstance;
import kr.ac.kaist.cdsn.lapras.learning.model.KNN;
import kr.ac.kaist.cdsn.lapras.util.Resource;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.net.*;
import java.util.Arrays;
import java.util.LinkedList;

import static java.lang.Thread.sleep;

/**
 * PresenceSensorAgent is a service agent which get presence data from
 * specific 'dataServer' and calculate presence of people 
 * and publish it
 * @author Heesuk Son (cdsn lab, heesuk.chad.son@gmail.com)
 * @since 2016-12-12
 *
 */

public class PresenceSensorAgent extends AgentComponent {
	private static final Logger LOGGER = LoggerFactory.getLogger(PresenceSensorAgent.class);
	private LinkedList<Long> intervalList = new LinkedList<Long>();

	// userPresence := {"empty", "present"}
	@ContextField(publishAsUpdated = true) public Context userPresence;

	public PresenceSensorAgent(EventDispatcher eventDispatcher, Agent agent) {
		super(eventDispatcher, agent);
	}

	private ArffDataInstance getStatistics(Long[] intervalArr){
		int totSigCnt = 0;
		int totBurstCnt = 0;
		long sigIntervalSum = 0;
		double sigIntervalAvg;

		for(int i=0; i<intervalArr.length-1; i++){
			if(intervalArr[i] > intervalArr[i+1]){
				totSigCnt++;
				sigIntervalSum += (intervalArr[i]-intervalArr[i+1]);
			}
		}
		if(totSigCnt == 0){
			sigIntervalAvg = intervalArr[intervalArr.length-1];
		}else{
			sigIntervalAvg = (double)sigIntervalSum / (double)totSigCnt;
		}

		for(int i=0; i<intervalArr.length-3; i++){
			if((intervalArr[i] > intervalArr[i+1] && intervalArr[i+1] > intervalArr[i+2])
					|| (intervalArr[i] > intervalArr[i+1] && intervalArr[i+1] > intervalArr[i+3])){
				totBurstCnt++;
			}
		}

		ArffDataInstance pStat = new ArffDataInstance(
				new String[]{totSigCnt+"",totBurstCnt+"",sigIntervalAvg+""});

		return pStat;
	}

	/**
	 * @param uPresence
	 *            userPresence. it should be one of "Present", "Likely",
	 *            "NoUser".
	 */
	public void setUserPresence(String uPresence) {
	    if (userPresence == null) return;
		if (userPresence.getValue() == null || !userPresence.getValue().equals(uPresence)) {
			LOGGER.info("{} -> {}", userPresence, uPresence);

			userPresence.updateValue(uPresence);
		} else {
			// LOGGER.info("{} -> {}", userPresence, uPresence);
		}
	}

	@Override
	public void run() {
		this.setUserPresence("empty");

		try {
			long startT = System.currentTimeMillis();
			while (true) {
				Socket sck = new Socket();
				SocketAddress serverAddress = new InetSocketAddress(
						Constants.N1_PRESENCE_SENSOR_DATA_SERVER_IP,
						Constants.PORT);
				try {
					sck.connect(serverAddress, 10000);
				} catch (ConnectException e) {
					e.printStackTrace();
					sck.close();
					continue;
				} catch (SocketTimeoutException e) {
					e.printStackTrace();
					sck.close();
					continue;
				}

				OutputStream out = sck.getOutputStream();
				DataOutputStream dout = new DataOutputStream(out);

				InputStream in = sck.getInputStream();
				DataInputStream din = new DataInputStream(in);

				dout.writeUTF(agent.getAgentConfig().getPlaceName());

				try {
					long timeFromLastSig = din.readLong();
					//LOGGER.info("Received event time : "+ timeFromLastSig);

					intervalList.add(timeFromLastSig);

					if(System.currentTimeMillis() - startT > Constants.DATA_PROCECCING_INTERVAL_UNIT){
						intervalList.pollFirst();
						ArffDataInstance queryData = getStatistics(intervalList.toArray(new Long[intervalList.size()]));
						//String presence = KNN.getInstance(Constants.K, Resource.pathOf(Constants.TRAIN_DATA_FILE)).
						//		getClassID(queryData.getValues());
						String presence = KNN.getInstance(Integer.parseInt(agent.getAgentConfig().getOption("k")),
								Resource.pathOf(agent.getAgentConfig().getOption("train_data_file"))).getClassID(queryData.getValues());
						LOGGER.info("User Presence for "+ Arrays.toString(queryData.getValues())+" = "+presence);
						setUserPresence(presence);
					}
				} catch (IOException e) {
					e.printStackTrace();
				}

				din.close();
				dout.close();
				sck.close();

				try {
					sleep(500);
				} catch (InterruptedException e) {
					e.printStackTrace();
				}
			}
		} catch (IOException e) {
			e.printStackTrace();
		}
	}
}
