package kr.ac.kaist.cdsn.lapras.agents.presence;


import kr.ac.kaist.cdsn.lapras.learning.data.ArffAttribute;
import kr.ac.kaist.cdsn.lapras.learning.data.ArffDataInstance;
import kr.ac.kaist.cdsn.lapras.learning.data.ArffDataset;
import kr.ac.kaist.cdsn.lapras.learning.data.ArffFileGen;
import kr.ac.kaist.cdsn.lapras.util.log.Logger;

import java.io.*;
import java.net.*;
import java.util.ArrayList;

/**
 * Created by chad1231 on 12/01/2017.
 */
public class SensorDataTrainThread implements Runnable{
	private String placeName;
	private long noSigInterval;
	private long dataProducingInterval;
	private long totalTrainDuration;
	private String label;
	private ArrayList<Long> intervalsWithNoSig;
	private ArrayList<ArffDataInstance> trainDataList;
	private final long RQST_INTERVAL = 300L;

	private ArffAttribute.AttrType[] attrTypeDef;

	public SensorDataTrainThread(String pName, long totalTrainDuration, long dataProducingInterval, String label) {
		this.placeName = pName;
		this.totalTrainDuration = totalTrainDuration;
		this.dataProducingInterval = dataProducingInterval;
		this.label = label;
		this.intervalsWithNoSig = new ArrayList<Long>();
		this.trainDataList = new ArrayList<ArffDataInstance>();
		this.noSigInterval = 0L;

		this.attrTypeDef = new ArffAttribute.AttrType[]
				{ArffAttribute.AttrType.NUMERIC,
						ArffAttribute.AttrType.NUMERIC,
						ArffAttribute.AttrType.NUMERIC};
	}

	public void run() {
		try {
			long startT = System.currentTimeMillis();
			while(System.currentTimeMillis() - startT < totalTrainDuration){
				long dataPDstartT = System.currentTimeMillis();

				while (System.currentTimeMillis() - dataPDstartT < dataProducingInterval) {
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

					dout.writeUTF(placeName);

					try {
						long rcv = din.readLong();
						Logger.debug("Received event time : "+rcv+"");
						intervalsWithNoSig.add(rcv);
					} catch (IOException e) {
						e.printStackTrace();
					}

					din.close();
					dout.close();
					sck.close();

					try {
						Thread.sleep(this.RQST_INTERVAL);
					} catch (InterruptedException e) {
						e.printStackTrace();
					}
				}

				this.procSensorData();
				intervalsWithNoSig.clear();
			}

			this.genTrainDataFile();
		} catch (IOException e) {
			e.printStackTrace();
		}
	}

	public void procSensorData(){
		Long[] intervalArr = intervalsWithNoSig.toArray(new Long[intervalsWithNoSig.size()]);
		int totSigCnt = 0;
		int totBurstCnt = 0;
		long sigIntervalSum = 0;
		double sigIntervalAvg;

		for(int i=0; i<intervalArr.length-1; i++){
			if(intervalArr[i] > intervalArr[i+1]){
				Logger.debug("totSigCnt++ >> [i] = "+intervalArr[i]+", [i+1] = "+intervalArr[i+1]);
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
				Logger.debug("totBurstCnt++ >> [i] = "+intervalArr[i]+", [i+1] = "+intervalArr[i+1]+", [i+2] = "+intervalArr[i+2]+", [i+3] = "+intervalArr[i+3]);
				totBurstCnt++;
			}
		}

		Logger.info("totSigCnt = "+totSigCnt + ", totBurstCnt = "+totBurstCnt + ", sigIntervalAvg = "+sigIntervalAvg);
		ArffDataInstance newData = new ArffDataInstance(this.attrTypeDef,
				new String[]{totSigCnt+"",totBurstCnt+"",sigIntervalAvg+""},this.label);
		this.trainDataList.add(newData);
	}

	public void genTrainDataFile(){
		ArffDataset newDS = new ArffDataset();
		newDS.setRelation("presence");
		newDS.setAttrWeight(new String[]{"1","1","1"});
		newDS.addClass("present");
		newDS.addClass("empty");
		newDS.addAttribute(new ArffAttribute("total_presence_sig_cnt",ArffAttribute.AttrType.NUMERIC));
		newDS.addAttribute(new ArffAttribute("total_sig_burst_cnt",ArffAttribute.AttrType.NUMERIC));
		newDS.addAttribute(new ArffAttribute("avg_sig_interval",ArffAttribute.AttrType.NUMERIC));

		for(ArffDataInstance data : this.trainDataList){
			newDS.addDataInstance(data);
		}

		ArffFileGen.genArffFile(newDS, Constants.TRAIN_DATA_OUTPUT_PATH);
	}
}
