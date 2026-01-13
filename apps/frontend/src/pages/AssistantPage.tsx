import Container from '../components/ui/Container';

export default function AssistantPage() {
  return (
    <Container as="main" className="py-6">
      <h1 className="text-2xl font-semibold">SmartMeal Assistant</h1>
      <p className="mt-2 text-sm text-gray-600">
        Nibble is getting ready to help you plan meals.
      </p>
    </Container>
  );
}
