import React from 'react';
import InteractionForm from './features/interactions/InteractionForm';
import Chat from './features/chat/Chat';

const InteractionPage: React.FC = () => (
  <div style={{ display: 'grid', gridTemplateColumns: '1fr 460px', gap: 12, height: '100%', minHeight: 0, overflow: 'hidden' }}>
    <div style={{ minHeight: 0, overflow: 'hidden' }}><InteractionForm /></div>
    <div style={{ minHeight: 0, overflow: 'hidden' }}><Chat /></div>
  </div>
);

export default InteractionPage;
