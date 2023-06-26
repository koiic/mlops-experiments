from ariadne import gql


type_defs = gql("""

   scalar DateTime
   scalar Dict

   interface Tag {
    id: ID!
    label: String!
    displayName: String!
    unit: String!
    tagEntries: [TagEntry]
    }
    
    type GatewayTag implements Tag {
        id: ID!
        label: String!
        displayName: String!
        unit: String!
        gateway: DataSource!
        tagEntries: [TagEntry]
    }
    
     type MLModelTag implements Tag {
        id: ID!
        label: String!
        displayName: String!
        unit: String!
        mlModelSchedule: MLModelScheduler
        tagEntries: [TagEntry]
    }

    type BooleanValue {
        value: Boolean
    }

    type FloatValue {
        value: Float
    }

    type IntValue {
        value: Int
    }

    type StringValue {
        value: String
    }

    union TagValue = BooleanValue | FloatValue | IntValue | StringValue
    
    union TagInterface = GatewayTag | MLModelTag

    type TagEntry {
        id: ID!
        tag: TagInterface!
        timestamp: Int!
        value: TagValue!
    }

    type DBConnector {
        id: ID!
        name: String!
        host: String!
        port: Int!
        user: String!
        password: String!
    }

    type MQTTConnector {
        id: ID!
        name: String!
        host: String!
        port: Int!
        user: String!
        password: String!
        topic: String!
    }

    type IoTCoreConnector {
        id: ID!
        name: String!
        host: String!
        port: Int!
        user: String!
        password: String!
        topic: String!
        privateKey: String!
        publicKey: String!
        certficate: String!
    }

    type LSTMModelParameters {
        id: ID!
        name: String!
        hiddenSize: Int
        sequenceLength: Int
        nLayers: [Int]
        dropout: [Int]
        learningRate: Float
        batchSize: Int
        numEpochs: Int
    }

    type VAEModelParameters {
        id: ID!
        name: String!
        hiddenSize: Int
        sequenceLength: Int
        nLayers: [Int]
        dropout: [Int]
        learningRate: Float
        batchSize: Int
        numEpochs: Int
    }
    
    type User{
        id: ID!
        name: String!
        email: String!
    }
        
    
    type MLModel {
        id: ID!
        name: String!
        description: String!
        createdBy: Int!
        createdAt: DateTime
        updatedAt: DateTime
        signature: MLModelSignature!
        versions: [MLModelVersion]
    }
    
    type MLModelSignature {
        id: ID!
        datasource: DataSource!
        inputTags: [TagInterface]
        outputTag: TagInterface
    }
    
    
    interface MlModelTagInterface {
        id: ID!
        label: String!
        unitType: String!
    }
    
    type MLModelInputTag implements MlModelTagInterface {
        id: ID!
        label: String!
        unitType: String!
    }
    
    type MLModelOutputTag implements MlModelTagInterface {
        id: ID!
        label: String!
        unitType: String!
    }
    
    type MLModelDeploymentConfig {
        id: ID!
        name: String!
        modelVersions: [MLModelVersion]
        configArn: String!
        }
        
    type MLModelDeployment {
        id: ID!
        name: String!
        endpointArn: String!
        endpointConfig: MLModelDeploymentConfig!
        createdAt: Int!
        updatedAt: Int!
    }

    union ModelParameters = LSTMModelParameters | VAEModelParameters

    enum MLModelVersionStatus {
        PENDING
        TRAINING
        TRAINED
        UNDEPLOYED
        DEPLOYED
    }
    
    enum ModelVersionType {
        ANOMALY_DETECTION
        TIME_SERIES_PREDICTION
    }
    
    type ModelTypeParameter {
        name: String!
        hiddenSize: Int
        sequenceLength: Int
        nLayers: [Int]
        dropout: [Int]
        learningRate: Float
        batchSize: Int
        numEpochs: Int
    }
    
    type ModelType {
        id: ID!
        name: String!
        description: String
        parameters: ModelTypeParameter
    }
    
    type DatasourceMap {
        datasourceId: Int!
        startTime: Int!
        endTime: Int!
    }

    type MLModelVersion {
        id: ID!
        name: String!
        parameters: Dict!
        status: MLModelVersionStatus
        modelType: ModelType
        version: Int!
        createdAt: DateTime!
        updatedAt: DateTime!
        mlModel: MLModel!
        modelPath: String
        datasourceMap: DatasourceMap
        archived: Boolean!
    }
    
    type MLModelScheduler {
        id: ID!
        modelVersion: MLModelVersion!
        datasourceId: Int
        startTime: Int!
        secondsToRepeat: Int!
        createdAt: DateTime
        createdBy: User!
    }
    
    enum TaskStatus {
        PENDING
        RUNNING
        FAILED
        SUCCESSFUL
    }
    
    type MLModelSchedulerTaskHistory{
        id: ID!
        counter: Int
        status: TaskStatus!
        failureReason: String
        errorMessage: String
        lastRun: Int
        startExecution: Int
        endExecution: Int
        executionDuration: Int
        successfulRun: Boolean
        modelVersion: MLModelVersion!
        executionResult: MLModelTag
    }
    
    type PageInfo {
        hasNextPage: Boolean!
        hasPreviousPage: Boolean!
        startCursor: String!
        endCursor: String!
    }
    
    type MLModelSchedulerHistoryPagination {
        pageInfo: PageInfo!
        data: [MLModelSchedulerTaskHistory]
    }

    type MLConnector {
        mlModelSchedule: [MLModelScheduler]
    }

    union Connector = DBConnector | MQTTConnector | IoTCoreConnector | MLConnector

    type DataSource {
        id: ID!
        name: String!
        connector: Connector!
        inputTags: [Tag]
        outputTags: [Tag]
        metadata: [Tag]
    }

    union dict_value = BooleanValue | FloatValue | IntValue | StringValue

    # type JSONMessage {
    #     [
    #         key: String
    #         value: String
    #     ]
    # }

    input MQTTConnectorInput {
        name: String!
        host: String!
        port: Int!
        user: String!
        password: String!
        topic: String!
    }

    input IoTCoreConnectorInput {
        name: String!
        host: String!
        port: Int!
        user: String!
        password: String!
        topic: String!
        privateKey: String!
        publicKey: String!
        certficate: String!
    }

    input DataSourceInput {
        name: String!
        # connector: Connector!
    }

    input TagInput {
        name: String!
        datasource: DataSourceInput!
    }

    input TagEntryInput {
        tag: TagInput!
        timestamp: Int!
        # value: TagValue!
    }
    
    input MLModelInputTagInput {
        label: String!
        unitType: String!
    }
    
    input MLModelOutputTagInput {
        label: String!
        unitType: String!
    }
        
    input MLModelSignatureInput {
        datasourceId: ID!
        inputTags: [ID!]
        outputTag: MLModelOutputTagInput
    }
    
    input MLModelCreateInput{
        name: String!
        description: String
        signature: MLModelSignatureInput
    }
    
     input MLModelUpdateInput{
        name: String
        description: String
        signature: MLModelSignatureInput
    }
    
    input MLModelVersionDatasourceMappingInput {
        datasourceId: ID!
        startTime: DateTime!
        endTime: DateTime!
    }
    
    input parameterInput {
        name: String!
        value: String!
    }
    
    input ModelParametersInput {
        parameters: [parameterInput]
    }
    
    input MLModelVersionInput {
        name: String!
        description: String
        parameters: [parameterInput]
        mlModelId: ID!
        modelTypeId: ID
        datasourceMapping: MLModelVersionDatasourceMappingInput
    }
    
    input MLModelVersionUpdateInput {
        name: String!
        description: String
        parameters: ModelParametersInput
        mlModelId: ID!
        datasourceMapping: MLModelVersionDatasourceMappingInput
    }
    
    input MLModelSchedulerInput {
        modelVersionId: ID!
        datasourceId: ID!
        startTime: DateTime!
        secondsToRepeat: Int!
    }
    
    input ModelTypeInput {
        name: String!
        description: String
        parameters: ModelParametersInput
    }
    

    type Mutation {
        createMQTTConnector(input: MQTTConnectorInput!): MQTTConnector!
        createIoTCoreConnector(input: IoTCoreConnectorInput): IoTCoreConnector!
        createDataSource(input: DataSourceInput!): DataSource!
        createTag(input: TagInput!): Tag!
        createTagEntry(input: TagEntryInput!): TagEntry!

        deleteMQTTConnector(id: ID!): Boolean!
        deleteIoTCoreConnector(id: ID!): Boolean!
        deleteDataSource(id: ID!): Boolean!
        deleteTag(id: ID!): Boolean!
        
        createMLModel(input: MLModelCreateInput!): MLModel!
        updateMLModel(id: ID!, input: MLModelUpdateInput!): MLModel!
        deleteMLModel(id: ID!): Boolean!
        
        createMLModelVersion(input: MLModelVersionInput!): MLModelVersion!
        updateMLModelVersion(id: ID!, input: MLModelVersionUpdateInput!): MLModelVersion!
        deleteMLModelVersion(id: ID!): Boolean!
        
        deployMLModelVersion(id: ID!): MLModelVersion!
        undeployMLModelVersion(id: ID!): MLModelVersion!
        trainMLModelVersion(id: ID!): MLModelVersion!
        
        createMLModelScheduler(input: MLModelSchedulerInput!): MLModelScheduler!
        deleteMLModelScheduler(id: ID!): Boolean!
        
        createModelType(input: ModelTypeInput!): ModelType!
        updateModelType(id: ID!, input: ModelTypeInput!): ModelType!
        deleteModelType(id: ID!): Boolean!
        
        
    }

    type Query {
        datasources: [DataSource]
        connector(id: ID!): Connector
        datasource(id: ID!): DataSource
        tag(id: ID!): Tag
        tagentry(id: ID!, start_time:Int!, end_time:Int): [TagEntry]
    
        mlmodels: [MLModel]
        mlmodel(id: ID!): MLModel
        
        mlmodelversions(model_id: ID!): [MLModelVersion]
        mlmodelversion(id: ID!): MLModelVersion
        
        modeltypes: [ModelType]
        modeltype(id: ID!): ModelType
        
        
        mlmodelschedulers(modelVersionId: ID!): [MLModelScheduler]
        mlmodelscheduler(id: ID!): MLModelScheduler
        
        mlmodelschedulertaskhistorypaginate(modelVersionId: ID!): MLModelSchedulerHistoryPagination
        mlmodelschedulertaskhistory(modelVersionId: ID!): [MLModelSchedulerTaskHistory]
        

        # get_last_message_from_connector(connector: Connector!): JSONMessage
    }
""")

