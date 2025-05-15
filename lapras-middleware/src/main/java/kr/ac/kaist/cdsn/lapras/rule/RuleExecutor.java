package kr.ac.kaist.cdsn.lapras.rule;

import kr.ac.kaist.cdsn.lapras.Agent;
import kr.ac.kaist.cdsn.lapras.Component;
import kr.ac.kaist.cdsn.lapras.action.ActionInstance;
import kr.ac.kaist.cdsn.lapras.context.ContextInstance;
import kr.ac.kaist.cdsn.lapras.event.Event;
import kr.ac.kaist.cdsn.lapras.event.EventDispatcher;
import kr.ac.kaist.cdsn.lapras.event.EventType;
import kr.ac.kaist.cdsn.lapras.util.Resource;
import org.apache.jena.datatypes.TypeMapper;
import org.apache.jena.datatypes.xsd.XSDDatatype;
import org.apache.jena.graph.Node;
import org.apache.jena.graph.NodeFactory;
import org.apache.jena.graph.Triple;
import org.apache.jena.query.*;
import org.apache.jena.rdf.model.InfModel;
import org.apache.jena.rdf.model.Model;
import org.apache.jena.rdf.model.ModelFactory;
import org.apache.jena.reasoner.rulesys.BuiltinRegistry;
import org.apache.jena.reasoner.rulesys.GenericRuleReasoner;
import org.apache.jena.reasoner.rulesys.Rule;
import org.apache.jena.reasoner.rulesys.RuleContext;
import org.apache.jena.reasoner.rulesys.builtins.BaseBuiltin;
import org.apache.jena.update.UpdateAction;
import org.apache.jena.update.UpdateRequest;
import org.apache.jena.util.iterator.ClosableIterator;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.List;

/**
 * Created by Daekeun Lee on 2016-11-15.
 */
public class RuleExecutor extends Component {
    private static final Logger LOGGER = LoggerFactory.getLogger(RuleExecutor.class);

    private static final String NS = "http://cdsn.kaist.ac.kr/lapras#";
    private GenericRuleReasoner ruleReasoner;
    private InfModel model;

    public RuleExecutor(EventDispatcher eventDispatcher, Agent agent) {
        super(eventDispatcher, agent);

        registerBuiltins();

        Model baseModel = ModelFactory.createDefaultModel();

        String ruleFilePath = agent.getAgentConfig().getOption("rule_file_path");
        if(ruleFilePath == null) {
            String ruleFileName = agent.getAgentConfig().getOption("rule_file_name");
            if(ruleFileName == null) {
                LOGGER.warn("Rule file not specified; RuleExecutor cannot be initialized");
                return;
            }
            ruleFilePath = Resource.pathOf(ruleFileName);
        }
        List<Rule> rules = Rule.rulesFromURL(ruleFilePath);
        ruleReasoner = new GenericRuleReasoner(rules);
        LOGGER.debug("Successfully loaded the rules from {}", ruleFilePath);

        model = ModelFactory.createInfModel(ruleReasoner, baseModel);
        LOGGER.debug("Created the ontology model");
    }

    private void registerBuiltins() {
        BuiltinRegistry.theRegistry.register(new BaseBuiltin() {
            @Override
            public String getName() {
                return "invoke";
            }

            @Override
            public void headAction(final Node[] args, final int length, final RuleContext context) {
                String functionalityName = (String) args[0].getLiteral().getValue();
                Object[] arguments = new Object[args.length - 1];
                for(int i=1;i<args.length;i++){
                    arguments[i-1] = args[i].getLiteral().getValue();
                }
                agent.getFunctionalityExecutor().invokeFunctionality(functionalityName, arguments);
            }
        });

        BuiltinRegistry.theRegistry.register(new BaseBuiltin() {
            @Override
            public String getName() {
                return "updateContext";
            }

            @Override
            public void headAction(final Node[] args, final int lentgh, final RuleContext context) {
                String contextName = (String) args[0].getLiteral().getValue();
                Object contextValue = args[1].getLiteralValue();
                agent.getContextManager().updateContext(contextName, contextValue, agent.getAgentConfig().getAgentName());
            }
        });

        BuiltinRegistry.theRegistry.register(new BaseBuiltin() {
            @Override
            public String getName() {
                return "contextDuration";
            }

            @Override
            public boolean bodyCall(Node[] args, int length, RuleContext context) {
                if(args.length != 2) {
                    throw new IllegalArgumentException("contextDuration builtin must be called with two arguments: contextName, variable");
                }
                String contextURI = args[0].getURI();
                Node contextNode = NodeFactory.createURI(contextURI);
                Node hasLastUpdateTimestamp = NodeFactory.createURI(NS + "hasLastUpdateTimestamp");
                ClosableIterator<Triple> iterator = context.find(contextNode, hasLastUpdateTimestamp, null);
                try {
                    if(iterator.hasNext()) {
                        Triple triple = iterator.next();
                        Long lastUpdateTimestamp = (Long) triple.getObject().getLiteralValue();
                        Node duration = NodeFactory.createLiteralByValue(System.currentTimeMillis() - lastUpdateTimestamp, triple.getObject().getLiteralDatatype());
                        context.getEnv().bind(args[1], duration);
                    } else {
                        context.getEnv().bind(args[1], NodeFactory.createLiteralByValue(-2147483648, XSDDatatype.XSDinteger));
                    }
                } finally {
                    iterator.close();
                }
                return true;
            }
        });

        BuiltinRegistry.theRegistry.register(new BaseBuiltin() {
            @Override
            public String getName() {
                return "noAction";
            }

            @Override
            public boolean bodyCall(Node[] args, int length, RuleContext context) {
                if(args.length != 2) {
                    throw new IllegalArgumentException("noAction builtin must be called with two arguments: actionName, withinTime");
                }
                String actionURI = args[0].getURI();
                Integer withinTime = (Integer) args[1].getLiteral().getValue();
                Node action = NodeFactory.createURI(actionURI);
                Node hasTimestamp = NodeFactory.createURI(NS + "hasTimestamp");
                ClosableIterator<Triple> iterator = context.find(action, hasTimestamp, null);
                try {
                    while (iterator.hasNext()) {
                        Triple triple = iterator.next();
                        Long timestamp = (Long) triple.getObject().getLiteralValue();
                        if (System.currentTimeMillis() - timestamp <= withinTime * 1000l) return false;
                    }
                } finally {
                    iterator.close();
                }
                return true;
            }
        });
    }

    @Override
    public void setUp() {
        for(ContextInstance contextInstance : agent.getContextManager().listContexts()) {
            ParameterizedSparqlString qString = new ParameterizedSparqlString();
            qString.setNsPrefix("lapras", NS);

            qString.setCommandText("INSERT DATA { " +
                    "?cn lapras:hasContextValue ?ncv;" +
                    "    lapras:hasTimestamp ?nt." +
                    "?npb lapras:publishesContext ?cn. } ");
            qString.setIri("cn", NS + contextInstance.getName());
            qString.setLiteral("ncv", contextInstance.getValue().toString(),
                    TypeMapper.getInstance().getTypeByClass(contextInstance.getValueType()));
            qString.setLiteral("nt", contextInstance.getTimestamp());
            qString.setIri("npb", NS + contextInstance.getPublisher());
            try {
                UpdateRequest updateRequest = qString.asUpdate();
                UpdateAction.execute(updateRequest, model);
            } catch(QueryException e) {
                LOGGER.error("An error occurred while executing the query {}", qString.toString(), e);
            }
        }
        model.validate();
    }

    @Override
    protected void subscribeEvents() {
        subscribeEvent(EventType.CONTEXT_UPDATED);
        subscribeEvent(EventType.ACTION_TAKEN);
    }

    @Override
    protected boolean handleEvent(Event event) {
        switch(event.getType()) {
            case CONTEXT_UPDATED: {
                ContextInstance contextInstance = (ContextInstance) event.getData();
                LOGGER.debug("Context updated: {} = {}", contextInstance.getName(), contextInstance.getValue());
                ParameterizedSparqlString qString = new ParameterizedSparqlString();
                qString.setNsPrefix("lapras", NS);

                boolean valueChanged = true;
                qString.setCommandText("SELECT ?cv WHERE {" +
                        "?cn lapras:hasContextValue ?cv." +
                        "}");
                qString.setIri("cn", NS + contextInstance.getName());
                try (QueryExecution qExec = QueryExecutionFactory.create(qString.asQuery(), model)) {
                    ResultSet results = qExec.execSelect();
                    if (results.hasNext()) {
                        QuerySolution solution = results.nextSolution();
                        valueChanged = !contextInstance.getValueType().equals(solution.get("cv").asLiteral().getValue());
                    }
                }

                UpdateRequest updateRequest;

                if(valueChanged) {
                    qString.setCommandText("DELETE WHERE { " +
                            "?cn lapras:hasLastUpdateTimestamp ?lut.}");
                    updateRequest = qString.asUpdate();
                    UpdateAction.execute(updateRequest, model);

                    qString.setCommandText("INSERT DATA { " +
                            "?cn lapras:hasLastUpdateTimestamp ?lut.}");
                    qString.setLiteral("lut", contextInstance.getTimestamp());
                    updateRequest = qString.asUpdate();
                    UpdateAction.execute(updateRequest, model);
                }

                qString.setCommandText("DELETE WHERE { " +
                        "?cn lapras:hasContextValue ?cv;" +
                        "    lapras:hasTimestamp ?t.}");
                qString.setIri("cn", NS + contextInstance.getName());
                updateRequest = qString.asUpdate();
                UpdateAction.execute(updateRequest, model);

                qString.setCommandText("INSERT DATA { " +
                        "?cn lapras:hasContextValue ?ncv;" +
                        "    lapras:hasTimestamp ?nt." +
                        "?npb lapras:publishesContext ?cn. } ");
                qString.setLiteral("ncv", contextInstance.getValue().toString(),
                        TypeMapper.getInstance().getTypeByClass(contextInstance.getValueType()));
                qString.setLiteral("nt", contextInstance.getTimestamp());
                qString.setIri("npb", NS + contextInstance.getPublisher());
                updateRequest = qString.asUpdate();
                UpdateAction.execute(updateRequest, model);

                LOGGER.debug("Updated context {} in the ontology model", contextInstance.getName());
                model.validate(); // Necessary to trigger the rule
                return true;
            }
            case ACTION_TAKEN: {
                ActionInstance actionInstance = (ActionInstance) event.getData();
                ParameterizedSparqlString qString = new ParameterizedSparqlString();
                qString.setNsPrefix("lapras", NS);
                qString.setCommandText("INSERT DATA {" +
                        "?an lapras:hasTimestamp ?t." +
                        "?pb lapras:publishesAction ?an.}");
                qString.setIri("an", NS + actionInstance.getName());
                qString.setLiteral("t", actionInstance.getTimestamp());
                qString.setIri("pb", NS + actionInstance.getPublisher());
                UpdateRequest updateRequest = qString.asUpdate();
                UpdateAction.execute(updateRequest, model);
                LOGGER.debug("Added action {} to the ontology model", actionInstance.getName());
                model.validate();
                return true;
            }
        }
        return false;
    }

    public List<Rule> listRules() {
        return ruleReasoner.getRules();
    }
}
