# Copyright 2015 Cisco Systems, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from cobra.internal.base.moimpl import BaseMo


class Mo(BaseMo):
    """Represents managed objects (MOs)

    Managed objects (MOs) represent a physical or logical entity with a set of
    configurations and properties.

    Attributes:
      dn (cobra.mit.naming.Dn): The distinguished name (Dn) of the managed
        object (MO) - readonly

      rn (cobra.mit.naming.Rn): The relative name (Rn) of the managed object
        (MO) - readonly

      status (cobra.internal.base.moimpl.MoStatus): The status of the MO -
        readonly

      parentDn (cobra.mit.naming.Dn): The parent managed object (MO)
        distinguished name (Dn) - readonly

      parent (cobra.mit.mo.Mo): The parent managed object (MO) - readonly

      dirtyProps (set): modified properties that have not been committed -
        readonly

      children (cobra.internal.base.moimpl.BaseMo._ChildContainer): A container
        for the children of this managed object - readonly

      numChildren (int): The number of direct decendents for this managed
        object - readonly

      contextRoot (None or cobra.mit.mo.Mo): The managed object that is the
        context root for this managed object
    """
    def __init__(self, parentMoOrDn, markDirty, *namingVals, **creationProps):
        """Initialize a managed object (MO)
        
        This should not be called directly.  Instead initialize the Mo from
        the model that you need.
        
        Args:
          parentMoOrDn (str or cobra.mit.naming.Dn or cobra.mit.mo.Mo): The
            parent managed object (MO) or distinguished name (Dn).
          markDirty (bool): If True, the MO is marked has having changes that
            need to be committed.  If False the Mo is not marked as having
            changes that need to be committed.
          *namingVals: Required values that are used to name the Mo, i.e. they
            become part of the MOs distinguished name.
          **creationProps: Properties to be set at the time the MO is created,
            these properties can also be set after the property is created if
            needed.
        
        Raises:
          NotImplementedError: If this class is called directly
        """
        if self.__class__ == Mo:
            raise NotImplementedError('Mo cannot be instantiated.')
        BaseMo.__init__(self, parentMoOrDn, markDirty, *namingVals,
                        **creationProps)

    def delete(self):
        """
        Marks the mo as deleted. If this mo is committed, the corresponding mo
        in the backend will be deleted.
        """
        BaseMo._delete(self)

    @property
    def dn(self): 
        return BaseMo._dn(self)

    @property
    def rn(self):
        return BaseMo._rn(self)

    @property
    def status(self):
        return BaseMo._status(self)

    @property
    def parentDn(self):
        return BaseMo._parentDn(self)

    @property
    def parent(self):
        return BaseMo._parent(self)

    @property
    def dirtyProps(self):
        return BaseMo._dirtyProps(self)

    @property
    def children(self):
        return BaseMo._children(self)

    @property
    def numChildren(self):
        return BaseMo._numChildren(self)

    @property
    def contextRoot(self):
        return self.dn.contextRoot

    def isPropDirty(self, propName):
        """Check if a property has been modified on this managed object
        
        Args:
          propName (str): The property name as a string

        Returns:
          bool: True if the property has been modified and not commited, False
            otherwise
        """    
        return BaseMo._isPropDirty(self, propName)

    def resetProps(self):
        """Resets managed object (MO) properties
        
        This will discard uncommitted changes.
        """    
        BaseMo._resetProps(self)

    def __getattr__(self, propName):
        return BaseMo.__getattr__(self, propName)

    def __setattr__(self, propName, propValue):
        BaseMo.__setattr__(self, propName, propValue)

