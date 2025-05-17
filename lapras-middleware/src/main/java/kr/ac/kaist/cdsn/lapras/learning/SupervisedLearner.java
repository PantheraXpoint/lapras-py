package kr.ac.kaist.cdsn.lapras.learning;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.AgentConfig;
import kr.ac.kaist.cdsn.lapras.Component;
import kr.ac.kaist.cdsn.lapras.context.ContextInstance;
import kr.ac.kaist.cdsn.lapras.event.Event;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.event.EventType;
import kr.ac.kaist.cdsn.lapras.learning.data.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.lang.reflect.InvocationTargetException;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.ArrayList;

import static javafx.scene.input.KeyCode.T;

/**
 * Created by chad1231 on 2017-04-19.
 */
public class SupervisedLearner extends Component{
    private static final Logger LOGGER = LoggerFactory.getLogger(SupervisedLearner.class);
    private SupervisedLearnerModel model;
    private String fPath = agent.getAgentConfig().getOption("train_data_file");
    private String modelType = agent.getAgentConfig().getOption("learner_model");

    private boolean collectingData = false;

    private ArffDataset trainData = new ArffDataset();
    private final ArrayList<String> currentDataInstance = new ArrayList<String>();
    private String currentClass = null;

    public SupervisedLearner(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        createLearnerModel();
    }

    private void createLearnerModel(){
        boolean fileExists = Files.exists(Paths.get(fPath));

        // [STEP 1] load train data set
        if(fileExists){
            trainData = ArffParser.getInstance(fPath).getDataset();
        }else{
            initDataset();
        }

        // [STEP 2] train a learner model with the loaded data set
        try {
            model = ((SupervisedLearnerModel) Class.forName("kr.ac.kaist.cdsn.lapras.learning.model."+modelType).
                    getConstructor().newInstance()).getInstance(agent, trainData);
        } catch (InstantiationException e) {
            e.printStackTrace();
        } catch (IllegalAccessException e) {
            e.printStackTrace();
        } catch (InvocationTargetException e) {
            e.printStackTrace();
        } catch (NoSuchMethodException e) {
            e.printStackTrace();
        } catch (ClassNotFoundException e) {
            e.printStackTrace();
        }
    }

    public void startDataCollection(){
        this.collectingData = true;
    }

    public void stopDataCollection(){
        this.collectingData = false;

        ArffFileGen.genArffFile(this.trainData, fPath);
    }

    public void reloadTrainedModel(){
        createLearnerModel();
    }

    public String getClassID(String[] query){
        return model.getClassID(query);
    }

    public void setClassList(String[] cList){
        trainData.setClassList(cList);
    }

    private void initDataset(){
        ArrayList<ArffAttribute> attrList = new ArrayList<ArffAttribute>();
        ArrayList<Double> attrWeight = new ArrayList<Double>();

        for (String featureName : agent.getAgentConfig().getOptionAsArray("feature_set")) {
            ArffAttribute attr = new ArffAttribute(featureName, ArffAttribute.AttrType.STRING); // TODO only with string?
            attrList.add(attr);
            attrWeight.add(new Double(1.0)); // default weight
            currentDataInstance.add("TO_BE_REPLACED_BY_FEATURE_VALUE");
        }

        trainData.setRelation(agent.getAgentConfig().getAgentName()+"_Learner_Train_Data");
        trainData.setAttrList(attrList);
        trainData.setAttrWeight(attrWeight);
    }

    public void setCurrentClass(String clazz){
        this.currentClass = clazz;
        this.currentDataInstance.set(currentDataInstance.size()-1, clazz);
    }

    @Override
    protected void subscribeEvents() {
        subscribeEvent(EventType.CONTEXT_UPDATED);
    }

    @Override
    protected boolean handleEvent(Event event) {
        switch(event.getType()) {
            case CONTEXT_UPDATED:
                ContextInstance contextInstance = (ContextInstance) event.getData();
                LOGGER.debug("Context updated: {} = {}", contextInstance.getName(), contextInstance.getValue());

                int index = this.getCtxIndex(contextInstance.getName());
                currentDataInstance.set(index, (String) contextInstance.getValue());

                if(this.currentClass != null){
                    addDataInstance();
                }

                return true;
        }

        return false;
    }

    public void setLocalFeatureValues(String[] values){
        for(int i=0; i<values.length; i++){
            this.currentDataInstance.set(i, values[i]);
        }

        if(this.currentClass != null){
            addDataInstance();
        }
    }

    private void addDataInstance(){
        if(this.collectingData == true){
            ArffDataInstance instance = new ArffDataInstance(this.trainData);
            String[] values = new String[this.currentDataInstance.size()-1];
            for(int i=0; i<values.length; i++){
                values[i] = this.currentDataInstance.get(i);
            }

            instance.setValues(values);
            instance.setClass(this.currentClass);

            this.trainData.addDataInstance(instance);
        }
    }

    private int getCtxIndex(String ctx){
        int i=0;
        for(ArffAttribute attr : trainData.getAttrList()){
            if(ctx.equals(attr))    return i;
            i++;
        }

        return -1;
    }
}
