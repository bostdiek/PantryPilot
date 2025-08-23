import { useState } from 'react';
import { Button } from './Button';
import { Dialog, DialogFooter } from './Dialog';

/**
 * DialogDemo component that demonstrates the usage of our Dialog component
 */
export function DialogDemo() {
  // State for different dialog examples
  const [isBasicOpen, setIsBasicOpen] = useState(false);
  const [isWithDescriptionOpen, setIsWithDescriptionOpen] = useState(false);
  const [isCustomSizeOpen, setIsCustomSizeOpen] = useState(false);
  const [isStaticOpen, setIsStaticOpen] = useState(false);
  const [isFormOpen, setIsFormOpen] = useState(false);

  return (
    <div className="space-y-8 p-6">
      {/* Basic Dialog */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Basic Dialog</h2>
        <Button onClick={() => setIsBasicOpen(true)}>Open Basic Dialog</Button>

        <Dialog
          isOpen={isBasicOpen}
          onClose={() => setIsBasicOpen(false)}
          title="Confirm Action"
        >
          <p className="text-gray-600">
            Are you sure you want to proceed with this action?
          </p>

          <DialogFooter
            onCancel={() => setIsBasicOpen(false)}
            onConfirm={() => {
              console.log('Confirmed!');
              setIsBasicOpen(false);
            }}
          />
        </Dialog>
      </section>

      {/* Dialog with Description */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Dialog with Description</h2>
        <Button onClick={() => setIsWithDescriptionOpen(true)}>
          Open Dialog with Description
        </Button>

        <Dialog
          isOpen={isWithDescriptionOpen}
          onClose={() => setIsWithDescriptionOpen(false)}
          title="Delete Recipe"
          description="This action cannot be undone. This will permanently delete the recipe and remove it from all meal plans."
        >
          <p className="text-gray-600">
            Please type <strong>delete</strong> to confirm.
          </p>

          <div className="mt-4">
            <input
              type="text"
              className="w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              placeholder="Type 'delete' to confirm"
            />
          </div>

          <DialogFooter
            onCancel={() => setIsWithDescriptionOpen(false)}
            confirmText="Delete"
            confirmProps={{ variant: 'danger' }}
            onConfirm={() => {
              console.log('Deleted!');
              setIsWithDescriptionOpen(false);
            }}
          />
        </Dialog>
      </section>

      {/* Different Size Dialogs */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Custom Size Dialog</h2>
        <Button onClick={() => setIsCustomSizeOpen(true)}>
          Open Large Dialog
        </Button>

        <Dialog
          isOpen={isCustomSizeOpen}
          onClose={() => setIsCustomSizeOpen(false)}
          title="Recipe Details"
          size="lg"
        >
          <div className="space-y-4">
            <p className="text-gray-600">
              This dialog uses a larger size to display more content.
            </p>

            <div className="rounded-md bg-gray-50 p-4">
              <h4 className="font-medium">Ingredients</h4>
              <ul className="mt-2 ml-5 list-disc">
                <li>2 cups flour</li>
                <li>1 tsp baking powder</li>
                <li>1/2 tsp salt</li>
                <li>1 cup sugar</li>
                <li>1/2 cup butter</li>
                <li>2 eggs</li>
                <li>1 tsp vanilla extract</li>
              </ul>
            </div>

            <div className="rounded-md bg-gray-50 p-4">
              <h4 className="font-medium">Instructions</h4>
              <ol className="mt-2 ml-5 list-decimal">
                <li>Preheat oven to 350°F (175°C)</li>
                <li>Mix dry ingredients in a bowl</li>
                <li>Cream butter and sugar in another bowl</li>
                <li>Add eggs and vanilla to butter mixture</li>
                <li>Combine dry and wet ingredients</li>
                <li>Pour into a greased pan</li>
                <li>Bake for 30 minutes</li>
              </ol>
            </div>
          </div>

          <DialogFooter onCancel={() => setIsCustomSizeOpen(false)} />
        </Dialog>
      </section>

      {/* Static Dialog (can't close by clicking outside) */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Static Dialog</h2>
        <Button onClick={() => setIsStaticOpen(true)}>
          Open Static Dialog
        </Button>

        <Dialog
          isOpen={isStaticOpen}
          onClose={() => setIsStaticOpen(false)}
          title="Important Information"
          static
        >
          <div className="text-gray-600">
            <p>
              This dialog can only be closed by clicking the buttons below.
              Clicking outside will not close it.
            </p>
            <div className="mt-4 rounded-md bg-blue-50 p-4 text-blue-800">
              <p className="font-medium">
                You must make a selection to continue.
              </p>
            </div>
          </div>

          <DialogFooter>
            <div className="flex w-full justify-between">
              <Button variant="danger" onClick={() => setIsStaticOpen(false)}>
                Decline
              </Button>
              <Button onClick={() => setIsStaticOpen(false)}>Accept</Button>
            </div>
          </DialogFooter>
        </Dialog>
      </section>

      {/* Form Dialog */}
      <section>
        <h2 className="mb-4 text-lg font-semibold">Form Dialog</h2>
        <Button onClick={() => setIsFormOpen(true)}>Open Form Dialog</Button>

        <Dialog
          isOpen={isFormOpen}
          onClose={() => setIsFormOpen(false)}
          title="Add New Recipe"
        >
          <form
            onSubmit={(e) => {
              e.preventDefault();
              console.log('Form submitted!');
              setIsFormOpen(false);
            }}
            className="space-y-4"
          >
            <div>
              <label
                htmlFor="name"
                className="block text-sm font-medium text-gray-700"
              >
                Recipe Name
              </label>
              <input
                type="text"
                id="name"
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label
                htmlFor="category"
                className="block text-sm font-medium text-gray-700"
              >
                Category
              </label>
              <select
                id="category"
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              >
                <option value="breakfast">Breakfast</option>
                <option value="lunch">Lunch</option>
                <option value="dinner">Dinner</option>
                <option value="dessert">Dessert</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="description"
                className="block text-sm font-medium text-gray-700"
              >
                Description
              </label>
              <textarea
                id="description"
                rows={3}
                className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
              ></textarea>
            </div>

            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setIsFormOpen(false)}
              >
                Cancel
              </Button>
              <Button type="submit">Save Recipe</Button>
            </DialogFooter>
          </form>
        </Dialog>
      </section>
    </div>
  );
}
