from ariadne import gql

type_defs = gql("""

    scalar DateTime
    scalar Dict
    scalar Any
    scalar JSON
    
    type DataSource {
        id: ID!
        name: String!
        tags: [TagInterface]
    }
    
    interface Tag {
        id: ID
        label: String
        displayName: String
        unit: String
        tagEntries: [TagEntry]
    }
    
    type GatewayTag implements Tag {
        id: ID
        label: String
        displayName: String
        unit: String
        gateway: DataSource
        tagEntries: [TagEntry]
    }
    
     type MLModelTag implements Tag {
        id: ID
        label: String
        displayName: String
        unit: String
        type: String
        tagEntries: [TagEntry]
    }
    
    union TagInterface = GatewayTag | MLModelTag
    
    type User {
        id: ID!
        name: String!
        email: String!
    }

    type MLModel {
        id: ID!
        name: String!
        description: String!
        createdBy: User
        createdAt: DateTime
        updatedAt: DateTime
        datasource: DataSource
        inputTags: [TagInterface]
        outputTag: TagInterface
        versions: [MLModelVersion]
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

    type TagEntry {
        id: ID!
        tag: TagInterface!
        timestamp: Int!
        value: TagValue!
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

    enum MLModelVersionStatus {
        PENDING
        TRAINING
        TRAINED
        UNDEPLOYED
        DEPLOYED
    }

    # type ModelTypeParameter {
    #     name: String
    #     hiddenSize: Int
    #     sequenceLength: Int
    #     nLayers: [Int]
    #     dropout: [Int]
    #     learningRate: Float
    #     batchSize: Int
    #     numEpochs: Int
    # }

    type MlAlgorithm {
        id: ID!
        name: String!
        description: String
        parameters: JSON
    }

    type DatasourceMap {
        datasourceId: Int!
        startTime: Int!
        endTime: Int!
    }

    type MLModelVersion {
        id: ID!
        name: String!
        status: MLModelVersionStatus
        algorithm: MlAlgorithm
        version: Int!
        createdAt: DateTime!
        updatedAt: DateTime!
        mlModel: MLModel!
        modelPath: String
        datasource: DataSource
        startTime: DateTime!
        endTime: DateTime!
        archived: Boolean!
        trainingPercentage: Int!
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
        modelScheduler: MLModelScheduler!
        executionResult: MLModelTag
    }

    input MLModelOutputTagInput {
        label: String!
        displayName: String!
        unit: String!
        type: String!
    }

    input MLModelCreateInput{
        name: String!
        description: String
        datasourceId: ID!
        inputTags: [ID!]
        outputTag: MLModelOutputTagInput
    }

     input MLModelUpdateInput{
        name: String
        description: String
        datasourceId: ID
        inputTags: [ID]
        outputTag: MLModelOutputTagInput
    }

    input MLModelVersionDatasourceMappingInput {
        datasourceId: ID!
        startTime: DateTime!
        endTime: DateTime!
    }
    
    input algorithmParameterInput {
        id: ID!
        parameters: JSON!
    }

    input MLModelVersionInput {
        name: String!
        mlModelId: ID!
        description: String
        algorithm: algorithmParameterInput
        datasourceId: ID
        startTime: DateTime
        endTime: DateTime
        trainingPercentage: Int
        parameters: JSON
    }

    input MLModelVersionUpdateInput {
        name: String
        trainingPercentage: Int
        description: String
        mlModelId: ID
        datasourceId: ID
        startTime: DateTime
        endTime: DateTime
        algorithm: algorithmParameterInput
    }

    input MLModelSchedulerInput {
        modelVersionId: ID!
        datasourceId: ID!
        startTime: DateTime!
        secondsToRepeat: Int!
    }

   input parameterInput {
        name: String!
        type: String!
        defaultValue: Any
    }
    
    input MlAlgorithmInput {
        name: String!
        description: String
        parameters: [parameterInput]
    }

    type Mutation {
    
        createDatasource(name: String!): DataSource!
        createMLModel(input: MLModelCreateInput!): MLModel!
        updateMLModel(id: ID!, input: MLModelUpdateInput!): MLModel!
        deleteMLModel(id: ID!): Boolean!

        createMLModelVersion(input: MLModelVersionInput!): MLModelVersion!
        updateMLModelVersion(id: ID!, input: MLModelVersionUpdateInput!): MLModelVersion!
        deleteMLModelVersion(id: ID!): Boolean!

        deployMLModelVersion(id: ID!): MLModelVersion!
        undeployMLModelVersion(id: ID!): MLModelVersion!

        createMLModelScheduler(input: MLModelSchedulerInput!): MLModelScheduler!
        deleteMLModelScheduler(id: ID!): Boolean!

        createMlAlgorithm(input: MlAlgorithmInput!): MlAlgorithm!
        updateMlAlgorithm(id: ID!, input: MlAlgorithmInput!): MlAlgorithm!
        deleteMlAlgorithm(id: ID!): Boolean!

    }

    type Query {
        datasources: [DataSource]
        datasource(id: ID!): DataSource
        tag(id: ID!): Tag
        tagentry(id: ID!, start_time:Int!, end_time:Int): [TagEntry]

        mlmodels: [MLModel]
        mlmodel(id: ID!): MLModel

        mlmodelversions(model_id: ID!): [MLModelVersion]
        mlmodelversion(id: ID!): MLModelVersion

        mlalgorithms: [MlAlgorithm]
        mlalgorithm(id: ID!): MlAlgorithm


        mlmodelschedulers(modelVersionId: ID!): [MLModelScheduler]
        mlmodelscheduler(id: ID!): MLModelScheduler

        mlmodelschedulertaskhistory(modelSchedulerId: ID!): [MLModelSchedulerTaskHistory]

    }
""")
