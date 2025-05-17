package kr.ac.kaist.cdsn.lapras.learning.model;

import kr.ac.kaist.cdsn.lapras.learning.SupervisedLearnerModel;
import kr.ac.kaist.cdsn.lapras.learning.data.ArffAttribute;
import kr.ac.kaist.cdsn.lapras.learning.data.ArffDataInstance;
import kr.ac.kaist.cdsn.lapras.learning.data.ArffDataset;
import kr.ac.kaist.cdsn.lapras.learning.data.ArffParser;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Arrays;
import java.util.Comparator;

/**
 * Created by chad1231 on 11/01/2017.
 */
public class KNN extends SupervisedLearnerModel {
	private static final Logger LOGGER = LoggerFactory.getLogger(KNN.class);

	private final boolean ATTR_NORMALIZED = true;

	private ArffDataset dataset;
	private ArffAttribute.AttrType[] attrTypeList;
	private boolean[] queryEmpty;

	private int K;
	// distance-class array
	// dcArr[i][0] : distance sum in the i'th data
	// dcArr[i][1] : class in the i'th data
	private String[][] dcArr;
	// distanceArr[i][j] = distance of i'th attribute type and j'th data row
	private double[][] distanceArr;

	private KNN(int K, String fName){
		super();
		this.K = K;

		dataset = ArffParser.getInstance(fName).getDataset();
		attrTypeList = dataset.getAttrTypeList();

		dcArr = new String[dataset.getSize()][2];
		distanceArr = new double[attrTypeList.length][dataset.getSize()];
	}

	public static KNN getInstance(int K, String fName){
		if(_instance == null){
			_instance = new KNN(K, fName);
		}

		return (KNN)_instance;
	}

	/**
	 *
	 * @param query A String array which contains the feature values of the given query
	 * @return The corresponding class to the given feature set
	 */
	public String getClassID(String[] query){
		//LOGGER.debug("----------------------getClassID()");

		queryEmpty = new boolean[query.length];
		for(int i=0; i<query.length; i++){
			queryEmpty[i] = (query[i]==null)?true:false;
			//LOGGER.debug("queryEmpty["+i+"] = "+queryEmpty[i]);
		}

		computeDistanceArray(query);
		if(this.ATTR_NORMALIZED == true) normalizeDistanceArray();
		return getMajorityClassID();
	}

	/**
	 *
	 * @param query	when an element in the given query array is null, then a distance computation ignores that attribute.
	 */
	private void computeDistanceArray(String[] query){
		//LOGGER.debug("----------------------computeDistanceArray()");

		for(int i=0; i<dataset.getSize(); i++){
			ArffDataInstance data = dataset.getData(i);

			for(int j=0; j<attrTypeList.length; j++){
				if(queryEmpty[j] == false){
					if(attrTypeList[j]==ArffAttribute.AttrType.NUMERIC){
						distanceArr[j][i] =	Math.abs(Double.parseDouble(query[j]) - Double.parseDouble(data.get(j)));
					}else /* STRING */{
						distanceArr[j][i] = (query[j].equals(data.get(j)))?0:1;
					}
				}
			}
		}

		/*
		LOGGER.debug("[AFTER COMPUTING DISTANCE]");
		for(int i=0; i<distanceArr[0].length; i++){
			String tmp = "";
			for(int j=0; j<distanceArr.length; j++){
				tmp += (distanceArr[j][i] + " ");
			}
			LOGGER.debug(tmp);
		}

		LOGGER.debug("-------------------------------------------------------");
		*/
	}

	private void normalizeDistanceArray(){
		//LOGGER.debug("----------------------normalizeDistanceArray()");
		// distanceMinMax[i][0] : minimum distance of i'th attribute type
		// distanceMinMax[i][1] : maximum distance of i'th attribute type
		double[][] distanceMinMax = new double[attrTypeList.length][2];

		// compute min and max values of the distance values to be used for normalization
		for(int i=0; i<attrTypeList.length; i++){
			if(queryEmpty[i] == false){
				distanceMinMax[i][0] /* min */ = Double.MAX_VALUE;
				distanceMinMax[i][1] /* max */ = Double.MIN_VALUE;

				for(int j=0; j<distanceArr[i].length; j++){
					if(distanceArr[i][j] < distanceMinMax[i][0]){
						distanceMinMax[i][0] = distanceArr[i][j];
					}

					if(distanceArr[i][j] > distanceMinMax[i][1]){
						distanceMinMax[i][1] = distanceArr[i][j];
					}
				}
			}
		}


		/*
		LOGGER.debug("[AFTER COMPUTING MIN-MAX]");
		for(int i=0; i<distanceMinMax.length; i++){
			String tmp = "";
			for(int j=0; j<distanceMinMax[i].length; j++){
				tmp += (distanceMinMax[i][j] + " ");
			}
			LOGGER.debug(tmp);
		}
		LOGGER.debug("-------------------------------------------------------");
		*/

		// normalize
		for(int i=0; i<attrTypeList.length; i++){
			if(queryEmpty[i] == false){
				for(int j=0; j<distanceArr[i].length; j++){
					distanceArr[i][j] = (distanceArr[i][j]-distanceMinMax[i][0])
							/(distanceMinMax[i][1]-distanceMinMax[i][0]);
				}
			}
		}

		/*
		LOGGER.debug("[AFTER NORMALIZING DISTANCE]");
		for(int i=0; i<distanceArr[0].length; i++){
			String tmp = "";
			for(int j=0; j<distanceArr.length; j++){
				tmp += (distanceArr[j][i] + " ");
			}
			LOGGER.debug(tmp);
		}
		LOGGER.debug("-------------------------------------------------------");
		*/
	}

	private String getMajorityClassID(){
		//LOGGER.debug("----------------------getMajorityClassID()");

		// sum normalized distances for the whole attributes
		for(int i=0; i<distanceArr[0].length; i++){
			double distSum = 0;

			for(int j=0; j<attrTypeList.length; j++){
				if(queryEmpty[j] == false){
					distSum += (((dataset.getAttrWeight()==null)?1:dataset.getAttrWeight().get(j))
							* Math.pow(distanceArr[j][i],2));
				}
			}
			distSum /= (double)attrTypeList.length;

			dcArr[i][0] = distSum+"";
			dcArr[i][1] = dataset.getData(i).getDClass();
		}

		/*
		for (final String[] s : dcArr) {
			LOGGER.debug(s[0] + " " + s[1]);
		}
		LOGGER.debug("-------------------------------------------------------");
		*/

		// sort distance-class array
		Arrays.sort(dcArr, new Comparator<String[]>() {
			@Override
			public int compare(final String[] entry1, final String[] entry2) {
				final Double dist1 = Double.parseDouble(entry1[0]);
				final Double dist2 = Double.parseDouble(entry2[0]);
				return dist1.compareTo(dist2);
			}
		});


		/*
		LOGGER.debug("[AFTER SORTING DCARR] dcArr.length = "+dcArr.length);
		for (final String[] s : dcArr) {
			LOGGER.debug(s[0] + " " + s[1]);
		}
		LOGGER.debug("-------------------------------------------------------");
		*/

		// get the answer class
		// classCntArr[i][0] : i'th class' count
		// classCntArr[i][1] : i'th class' name
		String[][] classCntArr = new String[dataset.getClassList().size()][2];
		for(int i=0; i<dataset.getClassList().size(); i++){
			classCntArr[i][0] = "0";
			classCntArr[i][1] = dataset.getClassList().get(i);
		}

		// count k nearest neighbors' classes
		for(int i=0; i<K; i++){
			String clazz = dcArr[i][1];
			for(int j=0; j<classCntArr.length; j++){
				if(classCntArr[j][1].equals(clazz)){
					classCntArr[j][0] = (Integer.parseInt(classCntArr[j][0])+1)+"";
				}
			}
		}

		//LOGGER.debug(">>>>>>>>>>>>>>>> [AFTER SORTING KNN CLASSES]");
		Arrays.sort(classCntArr, new Comparator<String[]>() {
			@Override
			public int compare(final String[] entry1, final String[] entry2) {
				final Integer cnt1 = Integer.parseInt(entry1[0]);
				final Integer cnt2 = Integer.parseInt(entry2[0]);
				return cnt2.compareTo(cnt1);
			}
		});

		for (final String[] s : classCntArr) {
			LOGGER.info(s[0] + " " + s[1]);
		}

		return classCntArr[0][1];
	}
}
