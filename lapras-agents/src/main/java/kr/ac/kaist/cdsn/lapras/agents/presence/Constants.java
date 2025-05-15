package kr.ac.kaist.cdsn.lapras.agents.presence;

/***
 * <Place Number> <Sensor Number> N1CNLab824 : 0 C08(3080) N1CDSNLab823 : 1
 * C06(3078), C07(3079) N1iDBLab822 : 2 C05(3077) N1Corridor822 : 3
 * C02(3074),C03(3075),C04(3076) N1Lounge8F : 4 C01(3073)
 * 
 * <Signal from sensors> SIGNAL_ON(event is occurred) : 1 SIGNAL_OFF(no signal)
 * : 0
 * 
 ***/

public class Constants {

	/****************** Agent Specific parameters ******************/

	static String N1_SEMINAR_ROOM_825_GLOBAL_IP = "143.248.56.213";
	// static String N1_SEMINAR_ROOM_825_LOCAL_IP = "192.168.0.104";
	static String N1_LOUNGE_8F_GLOBAL_IP = "143.248.53.13";
	// static String N1_LOUNGE_8F_8F_LOCAL_IP = "192.168.0.100";
	// static String N1_LOUNGE_8F_9F_GLOBAL_IP = "143.248.53.13";
	// static String N1_LOUNGE_8F_9F_LOCAL_IP = "192.168.0.100";

	static String M2M_SERVER_ADDRESS = "rmi://localhost/smartcon3_plcs";
	// static String M2M_EXTERNAL_PROGRAM =
	// "c:/m2mkorea/field_setting/Smartcon3_plcs.exe";

	static final String HOST = "127.0.0.1"; // define host & local loop-back
											// address (data server -> agent)
	static final int PORT = 19193; // define the port # (data server <- agent)
	static int MESSAGE_SIZE = 256; // define message size

	static final String N1_CNLAB_824_AGENT_IP = "";
	static final String N1_CDSNLAB_823_AGENT_IP = "";
	static final String N1_IDBLAB_822_AGENT_IP = "";
	static final String N1_CORRIDOR_822_AGENT_IP = "";
	static final String N1_LOUNGE_8F_AGENT_IP = "143.248.53.13";
	static final String N1_SEMINAR_825_AGENT_IP = "143.248.56.213"; //added

	static final String N1_PRESENCE_SENSOR_DATA_SERVER_IP = "143.248.55.237";

	public static final String N1SeminarRoom825_Name = "N1SeminarRoom825";
	public static final String N1Lounge8F_Name = "N1Lounge8F";
	public static final String N1Corridor823_Name = "N1Corridor823";
	public static final String N1Corridor822_Name = "N1Corridor822";
	public static final String N1CNLab824_Name = "N1CNLab824";
	public static final String N1CDSNLab823_Name = "N1CDSNLab823";
	public static final String N1iDBLab822_Name = "N1iDBLab822";

	static int PLACE_COUNT = 6; // how many places are in

	// this is bad code because any integer can be used for place number, so it
	// should be an enum or other
	static int N1_CNLAB_824 = 0;
	static int N1_CDSNLAB_823 = 1;
	static int N1_IDBLAB_822 = 2;
	static int N1_CORRIDOR_822 = 3;
	static int N1_LOUNGE_8F = 4;
	static int N1_SEMINAR_825 = 5; //added

	static int SIGNAL_ON = 1;
	static int SIGNAL_OFF = 0;

	// Multi-thread Pool Constants
	static int CORE_POOL_SIZE = 2;
	static int MAX_POOL_SIZE = 10;
	static long THREAD_ALIVE_TIME = 60L;

	// ---[START: Constant Values for Presence Sensor Agent Training & Testing ]---
	static long TOTAL_TRAIN_DURATION = 120000L;
	static long DATA_PROCECCING_INTERVAL_UNIT = 30000L;
	//static String TRAIN_LABEL = "present";
	static String TRAIN_LABEL = "empty";
	static String TRAIN_DATA_FILE = "n1_825_presence_train_data_170418_int30000.arff";
	static String TRAIN_DATA_OUTPUT_PATH = "lapras-agents/src/main/resources/"+TRAIN_DATA_FILE;
	// ----[END: Constant Values for Presence Sensor Agent Training & Testing ]----
}