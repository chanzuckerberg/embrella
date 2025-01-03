# EMbrella Next.js and React Frontend

## Prerequisites

Install the node version specified in `.nvmrc`. It is highly recommended to use a node version manager to manage multiple versions of node on your machine. Using a consistent version of node for the project ensures that any developer or deployed environment will have the same dependency versions installed.

A list of recommended node version managers is below:

- [`asdf`](https://asdf-vm.com/guide/introduction.html)
- ['nodenv'](https://github.com/nodenv/nodenv)
- ['nvm'](https://github.com/nvm-sh/nvm)

## Install Dependencies

1. `cd` into the `frontend` directory.
2. Run `yarn`.

## Run Frontend

1. `cd` into the `frontend` directory.
2. Run `yarn dev`.
3. Open browser at http://localhost:3000/next.

## Run Tests

1. `cd` into the `frontend` directory.
2. Run `yarn test`.

## Code overview and best practices

The code organization in this repo is based on the [fractal file structure documented here](https://docs.google.com/document/d/12KJ0nhZbpIBvMyo0Zga4dIXIxedhK5llpKbCSMnV1H8/edit?tab=t.0#heading=h.4paeu0ena9pg).

This information is current as of Dec 2024.

### Next Routing

- In `Next.js` applications, routes (URL paths in the app) are configured with folders in the `app` folder.
  - The `annotations` folder contains the component that is rendered for the `/annotations` URL, the `cryo_grids` folder is rendered for the `/cryo_grids` route, and so on.
  - A new view / route can be added by creating a folder with the desired name and component to render.
- Refer to [Next.js routing docs](https://nextjs.org/docs/app/building-your-application/routing) for more information on how routing works.

### Code structure for views

- Each top level app route renders the component in the `page.tsx` file in the route's folder.
  - For example, `app/annotations/page.tsx` component (which is rendered for the `/annotations` URL) invokes the `AnnotationsView` component at `app/components/AnnotationsView/AnnotationsView.tsx`.
- The current view components (`AnnotationsView`, `GridsView`, `TomogramsView`) all have the same UX pattern and APIs, and leverage the `TableStateProvider`, `EntityTable`, and `EntityTableFilters` common components that implement core functionality for the application.

### Details on common components

#### TableStateProvider

The `TableStateProvider` encapsulates a context and reducer to manage the filter, pagination, and sorting state of a table view. This component is based on [the "Scaling Up with Reducer and Context" page in the React docs](https://react.dev/learn/scaling-up-with-reducer-and-context).

#### EntityTable

The `EntityTable` component is a reusable component that fetches data from a given API endpoint and displays it in a table. The table component uses the SDS Table component.

#### EntityTableFilters and Filters

The `EntityTableFilters` component implements the filter side panel use in Embrella UI views. It uses the `Filters` component, which is based on the SDS `ComplexFilter` component.

### Checklist for adding a new view

This is a general checklist for adding a filterable table view with a similar API to existing views. These steps may need some modification depending on the details of the new view.

- [ ] Create new folder in `app/` to setup new route
- [ ] Duplicate folder for existing view (e.g. `app/components/AnnotationsView/`) and rename the duplicate to desired name.
- [ ] In the new view folder, update the name of the file and component in the `[Entity]View.tsx` file in the new view folder
- [ ] Update `constants/columns.ts` with desired table column definitions for the new view.
- [ ] Update `constants/filters.ts` with filter configs for the new view
- [ ] Update the following in the `types.ts` file in the new folder:
  - [ ] `[Entity]Data` type for new view
  - [ ] `[Entity]FilterId` enum
  - [ ] `[Entity]FilterCategory` type
  - [ ] `[Entity]FilterConfig` type
- [ ] Update the following in `app/common/components/EntityTable/types.ts`:
  - [ ] `ApiPrimaryEntityAttribute` type
  - [ ] `AccessorReturnType` type (if needed)
- [ ] Update the following in `app/common/types/tableState.ts`:
  - [ ] `EntityDataTypes` type with new `[entity]Data` type
- [ ] Update the following in `app/common/constants/api.ts`:
  - [ ] Add value in `API` enum for entity data endpoint
  - [ ] Add value in `API` enum for entity filter list endpoint
- [ ] Update the following in `app/ccommon/types/entity.ts`:
  - [ ] Add mapping for new API field to `[Entity]Data` type in `EntityAPIPrimaryAttributeToDataType` type
- [ ] Update the following types in `app/common/types/filter.ts` with the newly created types:
  - [ ] `EntityFilterId`
  - [ ] `EntityFilterCategories`
  - [ ] `EntityFilterConfigs`
