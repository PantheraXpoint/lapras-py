package kr.ac.kaist.cdsn.lapras.util.log;

/**
 * Basically, every Lapras agent prints log based on slf4j. However, since slf4j library has several dependencies,
 * it is not a proper method to write logs in a light-weight manner. kr.ac.kaist.cdsn.lapras.util.log.Logger is a
 * lighter logging method which can be leveraged for local testing/debugging purposes.
 *
 * Created by chad1231 on 12/01/2017.
 */
public class Logger {
	private static Logger _instance;
	private static LoggerPrintMode[] PRINT_MODE;

	private Logger(){
		PRINT_MODE = new LoggerPrintMode[] {LoggerPrintMode.INFO, LoggerPrintMode.ERROR, LoggerPrintMode.DEBUG}; //default
	}

	public static void setMode(LoggerPrintMode[] modeConf){
		if(_instance == null){
			_instance = new Logger();
		}

		_instance.PRINT_MODE = new LoggerPrintMode[modeConf.length];

		for(int i=0; i<modeConf.length; i++){
			PRINT_MODE[i] = modeConf[i];
		}
	}

	public static void info(String log){
		if(_instance == null){
			_instance = new Logger();
		}

		if(allowed(LoggerPrintMode.INFO)){
			System.out.println(log);
		}
	}

	public static void debug(String log){
		if(_instance == null){
			_instance = new Logger();
		}

		if(allowed(LoggerPrintMode.DEBUG)){
			System.out.println(log);
		}
	}

	public static void error(String log){
		if(_instance == null){
			_instance = new Logger();
		}

		if(allowed(LoggerPrintMode.ERROR)){
			System.out.println(log);
		}
	}

	private static boolean allowed(LoggerPrintMode qMode){
		for(LoggerPrintMode allowedMode : _instance.PRINT_MODE){
			if(allowedMode == qMode) return true;
		}

		return false;
	}
}
