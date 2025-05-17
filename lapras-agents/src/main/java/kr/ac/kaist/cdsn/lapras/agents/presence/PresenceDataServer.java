package kr.ac.kaist.cdsn.lapras.agents.presence;

import m2m.manager.SiteManager;
import m2m.model.device.Gateway;
import m2m.model.site.Site;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.io.*;
import java.net.ServerSocket;
import java.net.Socket;
import java.net.SocketException;
import java.util.ArrayList;
import java.util.Date;
import java.util.List;
import java.util.concurrent.SynchronousQueue;
import java.util.concurrent.ThreadPoolExecutor;
import java.util.concurrent.TimeUnit;

//Import for synchronous socket programming
//Imported for receiving sensing data (from API)
//Import for multi-thread pool management
//Imported for SmartIoT project

/**
 * 게이트웨이로부터 재실센서 정보를 얻어오고, 동시에 이를 각 재실에이전트에 보내주기 위한 클래스
 * PresenceDataServer is a data server that it gets presence data from
 * gateWay and send it to each smart agent.
 * @author Chungkwon Ryu (idbLab, ryuch91@kaist.ac.kr)
 * @since 2015-11-10
 * @date 2016-05-09
 * @see PresenceCheckingThread, and some inner classes
 *      
 * @version 2.1
 */
public class PresenceDataServer {
	private static final Logger LOGGER = LoggerFactory.getLogger(PresenceDataServer.class);
	/** Timedata for each place (in milisec) */
	private static List<Long> userPresenceTimeData = new ArrayList<Long>();
	/** Thread pool sending msg to each agents */
	private static ThreadPoolExecutor msgThreadPool;
	/** Gateway instance to get data from gateway */
	private List<Gateway> gatewayList = SiteManager.getInstance().getGatewayList();

	/** 
	 * Constructor : Initialize time data to 0 and msgThreadPool
	 */
	public PresenceDataServer() {
		for (int i = 0; i < Constants.PLACE_COUNT; i++) {
			userPresenceTimeData.add(0L);
		}
		msgThreadPool = new ThreadPoolExecutor(Constants.CORE_POOL_SIZE, Constants.MAX_POOL_SIZE,
				Constants.THREAD_ALIVE_TIME, TimeUnit.SECONDS, new SynchronousQueue<Runnable>());
	}

	/** 
	 * Main function for class
	 * @param args
	 * @return none */
	public static void main(String[] args) {
		PresenceDataServer ds = new PresenceDataServer();
		ds.init();
	}

	/** 
	 * Start thread(get presence info from gateway) and open socket to wait sending
	 * Flow : Gateway -> DataServer(here)
	 */
	public void init() {
		Site site = new Site();
		site.setServerAddr(Constants.M2M_SERVER_ADDRESS);

		try {
			SiteManager.getInstance().start(site); // getting data thread(implemented in external jar)

			PresenceCheckingThread pct = new PresenceCheckingThread(this, gatewayList);
			pct.start();

			PresenceReturnThread sot = new PresenceReturnThread();
			sot.start();
		} catch (Exception e) {
			e.printStackTrace();
		}
	}

	/** 
	 * Innerclass for socket opening and listening
	 * Agent request to connect, then it sends time data to that agent
	 */
	class PresenceReturnThread extends Thread {
		private String placeInfo;

		public PresenceReturnThread() {
			placeInfo = "";
		}

		public void run() {
			try {
				ServerSocket serverSck = new ServerSocket(Constants.PORT);
				//LOGGER.info("Ready for connecting...");
				while (true) {
					try {
						placeInfo = ""; //re-initialize
						//LOGGER.info("Listening...");
						Socket sck;
						try {
							sck = serverSck.accept();
						} catch (SocketException e) {
							sleep(300);
							if (serverSck.isClosed()) {
								//LOGGER.info("Server socket is closed. Restart..");
								serverSck = new ServerSocket(Constants.PORT);
							}
							continue;
						}

						InputStream in = sck.getInputStream();
						DataInputStream din = new DataInputStream(in);
						OutputStream out = sck.getOutputStream();
						DataOutputStream dout = new DataOutputStream(out);

						placeInfo = din.readUTF();
						
						//LOGGER.info("Request from : {} - {}", placeInfo, sck.getInetAddress());
						//LOGGER.info("Place Info : {}", placeInfo);
						long eventT = 0L;
						long currentT = 0L;
						long difference = 0L;
						
						try {
							switch (placeInfo) {
							case Constants.N1CNLab824_Name:
								dout.writeLong(getUserPresence(Constants.N1_CNLAB_824));
								break;
							case Constants.N1CDSNLab823_Name:
								dout.writeLong(getUserPresence(Constants.N1_CDSNLAB_823));
								break;
							case Constants.N1iDBLab822_Name:
								dout.writeLong(getUserPresence(Constants.N1_IDBLAB_822));
								break;
							case Constants.N1Corridor822_Name:
								dout.writeLong(getUserPresence(Constants.N1_CORRIDOR_822));
								break;
							case Constants.N1Lounge8F_Name:
								eventT = getUserPresence(Constants.N1_LOUNGE_8F);
								currentT = System.currentTimeMillis();
								difference = currentT - eventT;
								dout.writeLong(difference);
								break;
							case Constants.N1SeminarRoom825_Name:
								eventT = getUserPresence(Constants.N1_SEMINAR_825);
								currentT = System.currentTimeMillis();
								difference = currentT - eventT;
								dout.writeLong(difference);
							default:
								break;
							}
						} catch (IOException e) {
							e.printStackTrace();
						}

						//LOGGER.info("Close connection from {}...", sck.getInetAddress());
						din.close();
						dout.close();
						sck.close();

						sleep(300);
					} catch (Exception e) {
						serverSck.close();
						e.printStackTrace();
					}
				}
			} catch (IOException e) {
				e.printStackTrace();
			}
		}
	}

	/**
	 * @param placeNumber : {0-NWLAB,1-CDSNLAB,2-IDBLAB,3-CORRIDOR,4-LOUNGE,5-SEMINAR} 
	 * @param uPresence : event-time in millisecond
	 */
	public void setUserPresence(int placeNumber, long uPresence) {
		if (userPresenceTimeData.get(placeNumber) < uPresence) {
			Date date = new Date(uPresence);
			//DateFormat df = new SimpleDateFormat("MM:dd:HH:mm");
			//simpleDate = df.format(date);

			switch(placeNumber){
			case 0:
				//LOGGER.info("At CNLab: {}",date);
				break;
			case 1:
				//LOGGER.info("At CDSNLab: {}",date);
				break;
			case 2:
				//LOGGER.info("At iDBLab: {}",date);
				break;
			case 3:
				//LOGGER.info("At 8F Corridor: {}",date);
				break;
			case 4:
				LOGGER.info("----At 8F Lounge: {}",date);
				break;
			case 5:
				LOGGER.info("----At 8F Seminar Room: {}",date);
				break;
			default:
				break;
			}
			//LOGGER.info("At place {} : {} -> {}", new Object[] { placeNumber, userPresenceTimeData.get(placeNumber), uPresence });
			userPresenceTimeData.set(placeNumber, uPresence);
		} else {
			// LOGGER.info("{} -> {}",
			// this.userPresence.get(placeNumber).toString(), uPresence);
		}
	}

	public Long getUserPresence(int placeNumber) {
		return userPresenceTimeData.get(placeNumber);
	}
}