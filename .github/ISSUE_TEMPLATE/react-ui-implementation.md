# Feature: React-Based Front-End UI Implementation

## Description
Implement a modern React-based front-end application for the FinDataExtractorVanilla system. This provides a production-grade, scalable UI solution with better performance and user experience than Streamlit.

## Current State
-  REST API endpoints available
-  HITL API endpoints implemented
-  No front-end UI

## Requirements

### 1. Technology Stack
- **Framework**: React 18+ with TypeScript
- **Build Tool**: Vite or Create React App
- **State Management**: Redux Toolkit or Zustand
- **UI Library**: Material-UI (MUI) or Ant Design
- **Routing**: React Router
- **API Client**: Axios or React Query
- **PDF Viewer**: react-pdf or PDF.js
- **Forms**: React Hook Form
- **Styling**: CSS Modules or Styled Components

### 2. Application Structure
```
frontend/
├── src/
│   ├── components/
│   │   ├── common/
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── LoadingSpinner.tsx
│   │   │   └── ErrorBoundary.tsx
│   │   ├── invoice/
│   │   │   ├── InvoiceCard.tsx
│   │   │   ├── InvoiceList.tsx
│   │   │   ├── InvoiceDetail.tsx
│   │   │   └── InvoiceForm.tsx
│   │   ├── validation/
│   │   │   ├── ValidationPanel.tsx
│   │   │   ├── ConfidenceIndicator.tsx
│   │   │   ├── FieldEditor.tsx
│   │   │   └── ValidationChecklist.tsx
│   │   ├── pdf/
│   │   │   ├── PDFViewer.tsx
│   │   │   └── PDFControls.tsx
│   │   └── approval/
│   │       ├── ApprovalWorkflow.tsx
│   │       ├── ApprovalCard.tsx
│   │       └── ApprovalHistory.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── InvoiceList.tsx
│   │   ├── InvoiceDetail.tsx
│   │   ├── Validation.tsx
│   │   ├── Approval.tsx
│   │   └── Matching.tsx
│   ├── services/
│   │   ├── api.ts
│   │   ├── invoiceService.ts
│   │   └── validationService.ts
│   ├── store/
│   │   ├── slices/
│   │   │   ├── invoiceSlice.ts
│   │   │   └── authSlice.ts
│   │   └── store.ts
│   ├── hooks/
│   │   ├── useInvoice.ts
│   │   └── useValidation.ts
│   └── utils/
│       ├── formatters.ts
│       └── validators.ts
├── package.json
└── tsconfig.json
```

### 3. Key Features

#### 3.1 Dashboard
- Invoice statistics
- Recent invoices
- Quick actions
- Status overview

#### 3.2 Invoice List
- Table/grid view
- Filters and sorting
- Search functionality
- Pagination
- Bulk actions

#### 3.3 Invoice Detail/Validation
- Split view: PDF | Form
- Real-time confidence indicators
- Inline editing
- Auto-save
- Validation checklist

#### 3.4 Approval Workflow
- Multi-step approval process
- Approval history
- Comments/notes
- Rejection workflow

### 4. UI/UX Requirements

#### Design System
- Consistent color palette
- Typography scale
- Component library
- Icon system
- Spacing system

#### Responsive Design
- Mobile-first approach
- Breakpoints: mobile, tablet, desktop
- Touch-friendly interactions
- Adaptive layouts

#### Accessibility
- WCAG 2.1 AA compliance
- Keyboard navigation
- Screen reader support
- Focus management
- ARIA labels

#### Performance
- Code splitting
- Lazy loading
- Image optimization
- API response caching
- Debounced search

## Technical Implementation

### API Integration
```typescript
// services/api.ts
const api = axios.create({
  baseURL: process.env.REACT_APP_API_URL,
  timeout: 10000,
});

// services/invoiceService.ts
export const invoiceService = {
  getInvoice: (id: string) => api.get(`/api/hitl/invoice/${id}`),
  validateInvoice: (id: string, data: ValidationData) => 
    api.post(`/api/hitl/invoice/validate`, data),
  // ... other methods
};
```

### State Management
```typescript
// store/slices/invoiceSlice.ts
const invoiceSlice = createSlice({
  name: 'invoice',
  initialState: { invoices: [], currentInvoice: null },
  reducers: {
    setInvoices: (state, action) => { ... },
    setCurrentInvoice: (state, action) => { ... },
  },
});
```

### PDF Viewer Integration
```typescript
// components/pdf/PDFViewer.tsx
import { Document, Page } from 'react-pdf';

const PDFViewer = ({ invoiceId }) => {
  const [pdfUrl, setPdfUrl] = useState('');
  
  useEffect(() => {
    setPdfUrl(`/api/hitl/invoice/${invoiceId}/pdf`);
  }, [invoiceId]);
  
  return (
    <Document file={pdfUrl}>
      <Page pageNumber={1} />
    </Document>
  );
};
```

## Acceptance Criteria
- [ ] React application structure created
- [ ] Core pages implemented
- [ ] API integration working
- [ ] PDF viewer functional
- [ ] Confidence indicators displayed
- [ ] Validation workflow complete
- [ ] Approval workflow complete
- [ ] Responsive design verified
- [ ] Accessibility testing passed
- [ ] Performance optimized
- [ ] User testing completed

## Deployment Considerations
- **Build**: Production build optimization
- **Hosting**: Static site hosting (Vercel, Netlify, Azure Static Web Apps)
- **Environment**: Environment variables for API URL
- **CORS**: Configure CORS on API
- **Authentication**: Integration with auth system (if needed)

## Related Issues
- See issue: Front-End UI Design and Architecture
- See issue: Streamlit HITL UI (alternative approach)

## Priority
Medium - More complex but provides better UX and scalability

## Notes
- React provides better performance and user experience
- More suitable for production deployment
- Requires front-end development expertise
- Better for external-facing applications

