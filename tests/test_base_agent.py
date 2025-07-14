import unittest
from unittest.mock import Mock

from src.agents.base_agent import AgentType, BaseAgent, Message


class TestBaseAgent(unittest.TestCase):
    """Test base agent functionality, particularly message handling"""

    def setUp(self):
        """Set up test fixtures"""

        # Create a concrete implementation of BaseAgent for testing
        class TestAgent(BaseAgent):
            def process(self, input_data):
                return {"result": "processed"}

            def validate_input(self, input_data):
                return True

            def handle_message(self, message):
                return {"handled": True, "message_type": message.message_type}

        self.agent = TestAgent(AgentType.REQUIREMENTS)

    def test_send_message(self):
        """Test sending a message to another agent"""
        content = {"test": "data"}
        message_type = "test_message"
        recipient = AgentType.FABRIC

        message = self.agent.send_message(recipient, content, message_type)

        # Verify message properties
        self.assertEqual(message.sender, AgentType.REQUIREMENTS)
        self.assertEqual(message.recipient, recipient)
        self.assertEqual(message.content, content)
        self.assertEqual(message.message_type, message_type)

        # Verify message was added to history
        self.assertIn(message, self.agent.message_history)

    def test_receive_message_valid_recipient(self):
        """Test receiving a message intended for this agent"""
        message = Message(
            sender=AgentType.FABRIC,
            recipient=AgentType.REQUIREMENTS,
            content={"test": "data"},
            message_type="test_message",
        )

        result = self.agent.receive_message(message)

        # Verify message was processed
        self.assertEqual(result, {"handled": True, "message_type": "test_message"})
        # Verify message was added to history
        self.assertIn(message, self.agent.message_history)

    def test_receive_message_wrong_recipient(self):
        """Test receiving a message intended for another agent"""
        message = Message(
            sender=AgentType.FABRIC,
            recipient=AgentType.STITCH,  # Different recipient
            content={"test": "data"},
            message_type="test_message",
        )

        result = self.agent.receive_message(message)

        # Verify message was not processed
        self.assertIsNone(result)
        # Verify message was not added to history
        self.assertNotIn(message, self.agent.message_history)

    def test_message_history_tracking(self):
        """Test that message history is properly tracked"""
        self.assertEqual(len(self.agent.message_history), 0)

        # Send a message
        sent_message = self.agent.send_message(
            AgentType.FABRIC, {"test": "data"}, "test_send"
        )
        self.assertEqual(len(self.agent.message_history), 1)
        self.assertEqual(self.agent.message_history[0], sent_message)

        # Receive a message
        received_message = Message(
            sender=AgentType.FABRIC,
            recipient=AgentType.REQUIREMENTS,
            content={"response": "data"},
            message_type="test_receive",
        )
        self.agent.receive_message(received_message)
        self.assertEqual(len(self.agent.message_history), 2)
        self.assertEqual(self.agent.message_history[1], received_message)

    def test_agent_type_assignment(self):
        """Test that agent type is properly assigned"""
        self.assertEqual(self.agent.agent_type, AgentType.REQUIREMENTS)

    def test_message_handling_integration(self):
        """Test the complete message flow"""

        # Create two agents
        class SenderAgent(BaseAgent):
            def process(self, input_data):
                return {"result": "sender_processed"}

            def validate_input(self, input_data):
                return True

            def handle_message(self, message):
                return {"sender_handled": True}

        class ReceiverAgent(BaseAgent):
            def process(self, input_data):
                return {"result": "receiver_processed"}

            def validate_input(self, input_data):
                return True

            def handle_message(self, message):
                return {"receiver_handled": True, "content": message.content}

        sender = SenderAgent(AgentType.FABRIC)
        receiver = ReceiverAgent(AgentType.STITCH)

        # Send message from sender to receiver
        message = sender.send_message(
            AgentType.STITCH, {"data": "test"}, "coordination"
        )

        # Receiver processes the message
        result = receiver.receive_message(message)

        # Verify the flow
        self.assertEqual(
            result, {"receiver_handled": True, "content": {"data": "test"}}
        )
        self.assertEqual(len(sender.message_history), 1)
        self.assertEqual(len(receiver.message_history), 1)


if __name__ == "__main__":
    unittest.main()
