from ariadne import gql

type_defs = gql("""
   type Tag {
    id: ID!
    name: String!
    display_name: String!
    unit: String!
    tage_entries: [TagEntry]
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
        tag: Tag!
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
        private_key: String!
        public_key: String!
        certficate: String!
    }

    type LSTMModelParameters {
        id: ID!
        name: String!
        hidden_size: Int
        sequence_length: Int
        n_layers: [Int]
        dropout: [Int]
        learning_rate: Float
        batch_size: Int
        num_epochs: Int
    }

    type VAEModelParameters {
        id: ID!
        name: String!
        hidden_size: Int
        sequence_length: Int
        n_layers: [Int]
        dropout: [Int]
        learning_rate: Float
        batch_size: Int
        num_epochs: Int
    }

    union ModelParameters = LSTMModelParameters | VAEModelParameters

    enum ModelVersionStatus {
        UNDEPLOYED
        TRAINING
        TRAINED
        DEPLOYED
    }

    type MLModelVersion {
        id: ID!
        name: String!
        model_parameters: ModelParameters!
        model_version_status: ModelVersionStatus!
    }

    type MLConnector {
        ml_model_version: [MLModelVersion]
    }

    union Connector = DBConnector | MQTTConnector | IoTCoreConnector | MLConnector

    type DataSource {
        id: ID!
        name: String!
        connector: Connector!
        input_tags: [Tag]
        ouput_tags: [Tag]
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
        private_key: String!
        public_key: String!
        certficate: String!
    }

    input DataSourceInput {
        name: String!
        # connector: Connector!
    }

    input TagInput {
        name: String!
        data_source: DataSourceInput!
    }

    input TagEntryInput {
        tag: TagInput!
        timestamp: Int!
        # value: TagValue!
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
    }

    type Query {
        data_sources: [DataSource]

        connector(id: ID!): Connector
        data_source(id: ID!): DataSource
        tag(id: ID!): Tag
        tag_entry(id: ID!, start_time:Int!, end_time:Int): [TagEntry]

        # get_last_message_from_connector(connector: Connector!): JSONMessage
    }
""")

