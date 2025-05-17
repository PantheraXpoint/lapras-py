package kr.ac.kaist.cdsn.lapras.learning;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.learning.data.ArffAttribute;
import kr.ac.kaist.cdsn.lapras.learning.data.ArffDataset;
import kr.ac.kaist.cdsn.lapras.learning.data.ArffParser;

/**
 * Created by chad1231 on 20/04/2017.
 */
public abstract class SupervisedLearnerModel {
	protected static SupervisedLearnerModel _instance;

	protected ArffDataset dataset;
	protected ArffAttribute.AttrType[] attrTypeList;

	protected Agent agent;

	protected SupervisedLearnerModel(){}
	protected SupervisedLearnerModel(Agent agent, ArffDataset dataset){
		this.agent = agent;
		this.dataset = dataset;
		attrTypeList = dataset.getAttrTypeList();
	}

	public static SupervisedLearnerModel getInstance(Agent agent, ArffDataset dataset){
		if(_instance == null){
			_instance = new SupervisedLearnerModel(agent, dataset) {
				@Override
				public String getClassID(String[] query) {
					return null;
				}
			};
		}

		return _instance;
	}

	public abstract String getClassID(String[] query);
}
